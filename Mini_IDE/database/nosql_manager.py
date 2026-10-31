"""Conector NoSQL embebido de tipo clave-valor (dbm.dumb).

NO es MongoDB. dbm.dumb es una base de datos persistente de la biblioteca
estándar de Python. El gestor implementa colecciones documentales en JSON
sobre pares clave-valor. Diseñado para una demostración local monousuario.
"""
import dbm.dumb
import json
import re
from pathlib import Path
from time import perf_counter
from uuid import uuid4

_NAME = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')

class NoSQLDatabaseManager:
    def __init__(self):
        self.db_path = None

    def connect(self, db_path):
        self.db_path = None
        try:
            if not str(db_path).strip():
                raise ValueError('Indica una ruta para la base NoSQL.')
            path = Path(db_path).expanduser().resolve()
            path.parent.mkdir(parents=True, exist_ok=True)
            with dbm.dumb.open(str(path), 'c'):
                pass
            self.db_path = str(path)
            return {'success': True, 'message': f'[NoSQL CONECTADO] dbm clave-valor | Archivo: {path} | Sin servidor ni credenciales', 'mode': 'DBM_KEY_VALUE'}
        except (OSError, ValueError) as exc:
            return {'success': False, 'message': f'[ERROR NoSQL] {exc}', 'mode': 'ERROR'}

    def disconnect(self):
        self.db_path = None

    @staticmethod
    def _parse(text):
        text = text.strip()
        if not text:
            raise ValueError('Escribe una operación NoSQL.')
        if text.startswith('{'):
            item = json.loads(text)
            if not isinstance(item, dict):
                raise ValueError('El comando debe ser un objeto JSON.')
            return item
        # Soporte acotado de sintaxis MongoShell; NO implica usar MongoDB.
        m = re.fullmatch(r'db\.(createCollection|dropCollection)\s*\(\s*"([A-Za-z_]\w*)"\s*\)\s*;?', text, re.S)
        if m:
            return {'action':m.group(1),'collection':m.group(2)}
        m = re.fullmatch(r'db\.([A-Za-z_]\w*)\.(insertOne|insertMany|find|updateOne|deleteOne|deleteMany|drop)\s*\((.*)\)\s*;?', text, re.S)
        if not m:
            raise ValueError('Usa JSON de operación o un comando MongoShell compatible (JSON válido).')
        col,action,args = m.groups()
        if action == 'drop':
            return {'action':'dropCollection','collection':col}
        if action == 'find' and not args.strip():
            return {'action':'find','collection':col,'filter':{}}
        parsed = json.loads('[' + args + ']')
        obj = {'action':action,'collection':col}
        if action in ('insertOne','insertMany'):
            obj['document' if action == 'insertOne' else 'documents'] = parsed[0]
        elif action == 'find':
            obj['filter'] = parsed[0]
        elif action == 'updateOne':
            if len(parsed) != 2:
                raise ValueError('updateOne necesita filtro y {"$set": {...}}.')
            obj['filter'],obj['update'] = parsed
        elif action in ('deleteOne','deleteMany'):
            obj['filter'] = parsed[0]
        return obj

    @staticmethod
    def _match(doc, filt):
        if not isinstance(filt,dict):
            raise ValueError('El filtro debe ser un objeto JSON.')
        return all(doc.get(key) == val for key,val in filt.items())

    def list_collections(self):
        if not self.db_path:
            return []
        with dbm.dumb.open(self.db_path,'c') as db:
            return sorted(key.decode('utf-8').split(':',1)[1] for key in db.keys() if key.startswith(b'col:'))

    def execute_command(self, raw_command):
        start=perf_counter()
        base={'success':False,'category':'NoSQL','columns':[],'rows':[],'raw_json':'[]','elapsed_ms':0.0}
        if not self.db_path:
            return {**base,'message':'[ERROR NoSQL] Conecta primero.'}
        try:
            command=self._parse(raw_command)
            action=command.get('action')
            col=command.get('collection')
            valid={'createCollection','dropCollection','insertOne','insertMany','find','updateOne','deleteOne','deleteMany','listCollections'}
            if action not in valid:
                raise ValueError('Acción no admitida. Usa createCollection, insertOne, find, updateOne, deleteOne, etc.')
            if action != 'listCollections' and (not isinstance(col,str) or not _NAME.fullmatch(col)):
                raise ValueError('Nombre de colección inválido. Usa letras, números y guion bajo.')
            category = ('DDL NoSQL' if action in ('createCollection','dropCollection','listCollections') else 'DML NoSQL') + f' ({action})'
            data=[]
            with dbm.dumb.open(self.db_path,'c') as db:
                collkey=f'col:{col}'.encode()
                prefix=f'doc:{col}:'.encode()
                if action=='listCollections':
                    data=[{'coleccion':name} for name in sorted(key.decode().split(':',1)[1] for key in db.keys() if key.startswith(b'col:'))]
                elif action=='createCollection':
                    if collkey in db:
                        raise ValueError('La colección ya existe.')
                    db[collkey] = b'1'
                elif action=='dropCollection':
                    for key in list(db.keys()):
                        if key==collkey or key.startswith(prefix):
                            del db[key]
                else:
                    if collkey not in db:
                        raise ValueError(f'No existe la colección {col}. Crea la colección primero.')
                    if action == 'insertOne':
                        docs=[command.get('document')]
                    elif action == 'insertMany':
                        docs=command.get('documents')
                        if not isinstance(docs,list):
                            raise ValueError('documents debe ser una lista.')
                    else:
                        docs=None
                    if docs is not None:
                        if not docs or any(not isinstance(d,dict) for d in docs):
                            raise ValueError('Los documentos deben ser objetos JSON.')
                        for doc in docs:
                            ident=uuid4().hex[:12]
                            db[prefix+ident.encode()]=json.dumps(doc,ensure_ascii=False).encode('utf-8')
                        data=[{'insertados':len(docs)}]
                    else:
                        filt=command.get('filter',{})
                        if not isinstance(filt,dict):
                            raise ValueError('filter debe ser un objeto JSON.')
                        matches=[]
                        for key in sorted(db.keys()):
                            if key.startswith(prefix):
                                doc=json.loads(db[key].decode('utf-8'))
                                if self._match(doc,filt):
                                    matches.append((key,doc))
                        if action=='find':
                            data=[{'_id':key[len(prefix):].decode(),**doc} for key,doc in matches]
                        elif action=='updateOne':
                            update=command.get('update',{})
                            patch=update.get('$set') if isinstance(update,dict) else None
                            if not isinstance(patch,dict):
                                raise ValueError('Se requiere update: {"$set": {...}}.')
                            if matches:
                                key,doc=matches[0]
                                doc.update(patch)
                                db[key]=json.dumps(doc,ensure_ascii=False).encode('utf-8')
                            data=[{'actualizados':int(bool(matches))}]
                        elif action in ('deleteOne','deleteMany'):
                            selected=matches[:1] if action == 'deleteOne' else matches
                            for key,_ in selected:
                                del db[key]
                            data=[{'eliminados':len(selected)}]
            columns=list(dict.fromkeys(key for doc in data for key in doc))
            rows=[[json.dumps(d.get(c),ensure_ascii=False) if isinstance(d.get(c),(list,dict)) else d.get(c) for c in columns] for d in data]
            ms=round((perf_counter()-start)*1000,2)
            return {'success':True,'category':category,'message':f'[OK - {category}] {len(data)} resultado(s). ({ms} ms)',
                    'columns':columns,'rows':rows,'raw_json':json.dumps(data,ensure_ascii=False,indent=2),'elapsed_ms':ms}
        except (ValueError,TypeError,json.JSONDecodeError,OSError,KeyError,UnicodeError) as exc:
            return {**base, 'message':f'[ERROR NoSQL] {exc}', 'elapsed_ms':round((perf_counter()-start)*1000,2)}
