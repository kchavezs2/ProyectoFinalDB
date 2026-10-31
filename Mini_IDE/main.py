"""Mini IDE GUI para SQLite y NoSQL dbm (Python estándar, sin MongoDB)."""
import json
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox
from database.sql_manager import SQLDatabaseManager
from database.nosql_manager import NoSQLDatabaseManager

ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data'
DATA.mkdir(exist_ok=True)

TEMPLATES={
 'SQL · Crear tabla': ('SQL', '''CREATE TABLE IF NOT EXISTS estudiantes (\n  id INTEGER PRIMARY KEY AUTOINCREMENT,\n  carnet TEXT UNIQUE NOT NULL,\n  nombre TEXT NOT NULL,\n  promedio REAL NOT NULL\n);'''),
 'SQL · Insertar': ('SQL', '''INSERT OR IGNORE INTO estudiantes(carnet,nombre,promedio) VALUES\n ('2026-101','Ana',91.5), ('2026-102','Carlos',86.0), ('2026-103','Maria',95.2);'''),
 'SQL · Consultar': ('SQL', 'SELECT id,carnet,nombre,promedio FROM estudiantes ORDER BY promedio DESC;'),
 'SQL · Actualizar': ('SQL', "UPDATE estudiantes SET promedio=94.0 WHERE carnet='2026-102';"),
 'SQL · Eliminar': ('SQL', "DELETE FROM estudiantes WHERE carnet='2026-103';"),
 'SQL · Modificar tabla': ('SQL','ALTER TABLE estudiantes ADD COLUMN semestre INTEGER DEFAULT 1;'),
 'SQL · Eliminar tabla': ('SQL','DROP TABLE IF EXISTS estudiantes;'),
 'NoSQL · Crear colección': ('NoSQL', 'db.createCollection("proyectos")'),
 'NoSQL · Insertar documento': ('NoSQL', '''db.proyectos.insertOne({"codigo":"P-01","titulo":"Mini IDE","activo":true,"tecnologias":["Python","SQLite"]})'''),
 'NoSQL · Insertar varios': ('NoSQL','''db.proyectos.insertMany([{"codigo":"P-02","titulo":"Proyecto B","activo":true},{"codigo":"P-03","titulo":"Proyecto C","activo":false}])'''),
 'NoSQL · Consultar': ('NoSQL','db.proyectos.find({})'),
 'NoSQL · Actualizar': ('NoSQL','db.proyectos.updateOne({"codigo":"P-01"},{"$set":{"activo":false}})'),
 'NoSQL · Eliminar documento': ('NoSQL','db.proyectos.deleteOne({"codigo":"P-03"})'),
 'NoSQL · Eliminar colección': ('NoSQL','db.dropCollection("proyectos")'),
}

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Mini IDE Híbrido | SQLite + NoSQL dbm')
        self.geometry('1080x740'); self.minsize(820,560)
        self.sql=SQLDatabaseManager(); self.nosql=NoSQLDatabaseManager()
        style=ttk.Style(self)
        if 'clam' in style.theme_names(): style.theme_use('clam')
        bg='#111827'; panel='#1f2937'; text='#eef2ff'; accent='#15b8a6'
        self.configure(bg=bg)
        style.configure('.',background=panel,foreground=text,font=('Segoe UI',10))
        style.configure('TFrame',background=bg)
        style.configure('TLabelframe',background=bg,foreground=text)
        style.configure('TLabelframe.Label',background=bg,foreground=text,font=('Segoe UI',10,'bold'))
        style.configure('TButton',padding=6,background='#374151',foreground=text)
        style.map('TButton',background=[('active','#4b5563')])
        style.configure('TEntry',fieldbackground='#f9fafb',foreground='#111827')
        style.configure('TCombobox',fieldbackground='#f9fafb',foreground='#111827')
        style.configure('Treeview',background=panel,foreground=text,fieldbackground=panel,rowheight=26)
        style.configure('Treeview.Heading',background='#374151',foreground=text)
        style.configure('TNotebook',background=bg)
        style.configure('TNotebook.Tab',padding=(16,8))

        head=ttk.Frame(self);head.pack(fill='x',padx=14,pady=(12,6))
        tk.Label(head,text='MINI IDE  |  SQL + NoSQL',font=('Segoe UI',20,'bold'),bg=bg,fg='#f9fafb').pack(side='left')
        tk.Label(head,text='Sin MongoDB · NoSQL dbm clave-valor',bg=bg,fg='#9ca3af',font=('Segoe UI',10)).pack(side='right')
        conn=ttk.Frame(self);conn.pack(fill='x',padx=14,pady=5)
        self.sql_path=tk.StringVar(value=str(DATA/'universidad_sql.db'))
        self.nosql_path=tk.StringVar(value=str(DATA/'universidad_nosql'))
        row1=ttk.Frame(conn);row1.pack(fill='x',pady=3)
        tk.Label(row1,text='SQLite',width=12,anchor='w',bg=bg,fg=text).pack(side='left')
        ttk.Entry(row1,textvariable=self.sql_path).pack(side='left',fill='x',expand=True,padx=5)
        ttk.Button(row1,text='Conectar SQL',command=self.connect_sql).pack(side='left')
        row2=ttk.Frame(conn);row2.pack(fill='x',pady=3)
        tk.Label(row2,text='NoSQL dbm',width=12,anchor='w',bg=bg,fg=text).pack(side='left')
        ttk.Entry(row2,textvariable=self.nosql_path).pack(side='left',fill='x',expand=True,padx=5)
        ttk.Button(row2,text='Conectar NoSQL',command=self.connect_nosql).pack(side='left')
        ttk.Button(conn,text='Conectar ambas bases',command=self.connect_both).pack(anchor='e',pady=(4,0))
        self.status=tk.StringVar(value='Desconectado. Pulsa "Conectar ambas bases".')
        tk.Label(self,textvariable=self.status,anchor='w',bg=bg,fg='#5eead4').pack(fill='x',padx=14,pady=(0,6))

        body=ttk.Panedwindow(self,orient='horizontal');body.pack(fill='both',expand=True,padx=14,pady=6)
        left=ttk.Labelframe(body,text=' Estructuras ');body.add(left,weight=1)
        self.explorer=tk.Listbox(left,bg=panel,fg=text,selectbackground='#0f766e',highlightthickness=0,font=('Consolas',11),border=0)
        self.explorer.pack(fill='both',expand=True,padx=5,pady=6)
        ttk.Button(left,text='Actualizar lista',command=self.refresh).pack(fill='x',padx=5,pady=(0,6))
        right=ttk.Frame(body);body.add(right,weight=4)
        toolbar=ttk.Frame(right);toolbar.pack(fill='x',pady=(0,6))
        tk.Label(toolbar,text='Motor:',bg=bg,fg=text).pack(side='left')
        self.engine=tk.StringVar(value='SQL')
        engines=ttk.Combobox(toolbar,textvariable=self.engine,values=('SQL','NoSQL'),state='readonly',width=9)
        engines.pack(side='left',padx=(6,12));engines.bind('<<ComboboxSelected>>',lambda e:self.refresh())
        tk.Label(toolbar,text='Plantilla:',bg=bg,fg=text).pack(side='left')
        self.tpl=tk.StringVar(value='SQL · Crear tabla')
        templates=ttk.Combobox(toolbar,textvariable=self.tpl,values=list(TEMPLATES),state='readonly',width=27)
        templates.pack(side='left',fill='x',expand=True,padx=(6,8));templates.bind('<<ComboboxSelected>>',self.load_template)
        ttk.Button(toolbar,text='Cargar',command=self.load_template).pack(side='left')
        editor_frame=ttk.Labelframe(right,text=' Editor de comandos ');editor_frame.pack(fill='both',expand=True)
        self.editor=tk.Text(editor_frame,height=10,bg='#0b1220',fg='#e5e7eb',insertbackground='white',font=('Consolas',11),wrap='word',undo=True,padx=12,pady=10)
        self.editor.pack(fill='both',expand=True,padx=5,pady=5)
        actions=ttk.Frame(right);actions.pack(fill='x',pady=5)
        ttk.Button(actions,text='▶ Ejecutar  F5',command=self.execute).pack(side='left')
        ttk.Button(actions,text='Limpiar editor',command=lambda:self.editor.delete('1.0','end')).pack(side='left',padx=8)
        self.info=tk.StringVar(value='Listo.');tk.Label(actions,textvariable=self.info,anchor='e',bg=bg,fg='#e5e7eb').pack(side='right',fill='x',expand=True)
        notebook=ttk.Notebook(right);notebook.pack(fill='both',expand=True)
        t1=ttk.Frame(notebook);t2=ttk.Frame(notebook);notebook.add(t1,text='Resultados (tabla)');notebook.add(t2,text='JSON y mensajes')
        self.table=ttk.Treeview(t1,columns=(),show='headings');self.table.pack(fill='both',expand=True,pady=6)
        self.log=tk.Text(t2,height=9,bg='#0b1220',fg='#d1d5db',font=('Consolas',10),wrap='word',padx=10,pady=8)
        self.log.pack(fill='both',expand=True,pady=6)
        self.bind('<F5>',lambda event:self.execute())
        self.protocol('WM_DELETE_WINDOW',self.close)
        self.load_template();self.connect_both()

    def connect_sql(self):
        r=self.sql.connect(self.sql_path.get());self.add_log(r['message']);self.status.set(r['message']);self.refresh();return r
    def connect_nosql(self):
        r=self.nosql.connect(self.nosql_path.get());self.add_log(r['message']);self.status.set(r['message']);self.refresh();return r
    def connect_both(self):
        a=self.connect_sql();b=self.connect_nosql()
        self.status.set(f'SQL: {"CONECTADO" if a["success"] else "ERROR"}    |    NoSQL dbm: {"CONECTADO" if b["success"] else "ERROR"}')
    def load_template(self,event=None):
        motor,command=TEMPLATES[self.tpl.get()]
        self.engine.set(motor);self.editor.delete('1.0','end');self.editor.insert('1.0',command);self.refresh()
    def add_log(self,text):
        self.log.insert('end',str(text)+'\n');self.log.see('end')
    def refresh(self):
        self.explorer.delete(0,'end')
        if self.engine.get()=='SQL':
            items=self.sql.list_tables();prefix='Tabla: '
        else:
            items=self.nosql.list_collections();prefix='Colección: '
        for item in items:self.explorer.insert('end',prefix+item)
        if not items:self.explorer.insert('end','(sin estructuras)')
    def execute(self):
        raw=self.editor.get('1.0','end').strip()
        if not raw:return
        if self.engine.get()=='SQL':
            result=self.sql.execute_query(raw)
        else:
            result=self.nosql.execute_command(raw)
        self.add_log(result['message'])
        if result.get('raw_json'):
            self.add_log(result['raw_json'])
        self.info.set(result['message'][:90])
        columns=result.get('columns',[]);rows=result.get('rows',[])
        self.table.delete(*self.table.get_children())
        self.table['columns']=columns
        for c in columns:
            self.table.heading(c,text=c)
            self.table.column(c,width=125,minwidth=90,stretch=True)
        for r in rows:
            self.table.insert('','end',values=['' if v is None else str(v) for v in r])
        self.refresh()
    def close(self):
        self.sql.disconnect();self.nosql.disconnect();self.destroy()

if __name__=='__main__':
    App().mainloop()
