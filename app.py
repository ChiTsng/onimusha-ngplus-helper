"""Chinese desktop UI; game saves are processed entirely offline."""
import queue
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import webbrowser
import core
import i18n
import chest_labels
import privacy
from i18n import tr


class App(tk.Tk):
    def __init__(self,language='zh',initial=None):
        super().__init__()
        i18n.set_language(language)
        self.next_language=None
        self.title(tr('鬼武者 · 周目继承助手 0.10'))
        self.geometry(f'1160x{min(960,self.winfo_screenheight()-100)}');self.minsize(960,680)
        self.configure(background='#eef2f5')
        self.ui_font='Yu Gothic UI' if language=='ja' else ('Segoe UI' if language=='en' else 'Microsoft YaHei UI')
        self.option_add('*Font',(self.ui_font,10))
        style=ttk.Style(self);style.theme_use('clam')
        # Arrowless, low-contrast scrollbars shared by the page, preview and chest list.
        style.layout('Vertical.TScrollbar',[
            ('Vertical.Scrollbar.trough',{'sticky':'ns','children':[
                ('Vertical.Scrollbar.thumb',{'expand':'1','sticky':'nswe'})]})])
        style.configure('Vertical.TScrollbar',width=8,arrowsize=8,borderwidth=0,
                        relief='flat',background='#c5d0d6',troughcolor='#eef2f5',
                        bordercolor='#eef2f5',lightcolor='#c5d0d6',darkcolor='#c5d0d6',
                        gripcount=0)
        style.map('Vertical.TScrollbar',
                  background=[('pressed','#8a9da8'),('active','#a7b7c0')],
                  lightcolor=[('pressed','#8a9da8'),('active','#a7b7c0')],
                  darkcolor=[('pressed','#8a9da8'),('active','#a7b7c0')])
        style.configure('.',font=(self.ui_font,10),foreground='#263747',background='#ffffff')
        style.configure('TFrame',background='#ffffff')
        style.configure('Page.TFrame',background='#eef2f5')
        style.configure('TLabel',padding=0)
        style.configure('Muted.TLabel',foreground='#647586')
        style.configure('Title.TLabel',font=(self.ui_font,12,'bold'))
        style.configure('TButton',padding=(16,9),borderwidth=0,background='#eaf0f4',foreground='#263747',focusthickness=2,focuscolor='#168577')
        style.map('TButton',background=[('active','#dce7ed'),('disabled','#f1f4f6')],foreground=[('disabled','#95a2ad')])
        style.configure('Accent.TButton',background='#127d71',foreground='white')
        style.map('Accent.TButton',background=[('disabled','#c8d9d6'),('active','#09675e')],foreground=[('disabled','#718f88'),('!disabled','white')])
        style.configure('TEntry',padding=8,borderwidth=1,fieldbackground='#f7f9fb',bordercolor='#dce4ea',lightcolor='#dce4ea',darkcolor='#dce4ea')
        style.configure('TCombobox',padding=7,borderwidth=1,fieldbackground='#f7f9fb',bordercolor='#dce4ea',arrowsize=14)
        style.map('TCombobox',fieldbackground=[('readonly','#f7f9fb')],selectbackground=[('readonly','#dceeea')],selectforeground=[('readonly','#263747')])
        style.configure('TCheckbutton',padding=4,background='#ffffff')
        style.map('TCheckbutton',foreground=[('disabled','#8e9ba6')],background=[('active','#ffffff')])
        # Keep native checkbutton keyboard/variable semantics; replace only its X indicator.
        self.check_images=[]
        for selected,disabled in ((False,False),(True,False),(False,True),(True,True)):
            icon=tk.PhotoImage(master=self,width=24,height=22)
            edge='#cdd6dc' if disabled else ('#127d71' if selected else '#8398a6')
            fill=('#d8e4e1' if disabled else '#127d71') if selected else ('#f1f4f6' if disabled else '#ffffff')
            icon.put(edge,to=(1,2,19,20));icon.put(fill,to=(2,3,18,19))
            if selected:
                color='#91aaa3' if disabled else '#ffffff'
                for x,y in [(5,10),(6,11),(7,12),(8,13),(9,12),(10,11),(11,10),(12,9),(13,8),(14,7)]:
                    icon.put(color,to=(x,y,x+2,y+2))
            self.check_images.append(icon)
        off,on,disabled_off,disabled_on=self.check_images
        style.element_create('Modern.indicator','image',off,('disabled','selected',disabled_on),('disabled',disabled_off),('selected',on))
        style.layout('Modern.TCheckbutton',[('Checkbutton.padding',{'sticky':'nswe','children':[
            ('Modern.indicator',{'side':'left','sticky':''}),
            ('Checkbutton.focus',{'side':'left','sticky':'w','children':[('Checkbutton.label',{'sticky':'nswe'})]})]})])
        style.configure('Choice.TRadiobutton',font=(self.ui_font,12,'bold'),padding=(0,5))
        style.configure('Treeview',rowheight=38,borderwidth=0,fieldbackground='#ffffff')
        style.configure('Treeview.Heading',padding=10,background='#eaf0f4',font=(self.ui_font,10,'bold'),relief='flat')
        style.map('Treeview',background=[('selected','#dceeea')],foreground=[('selected','#125b51')])
        self.path=tk.StringVar();self.sid=tk.StringVar();self.source=tk.StringVar();self.target=tk.StringVar()
        self.path_display=tk.StringVar();self.revealed=False;self.discovered_paths=[];self.syncing_path=False;self.log_raw=''
        self.mode=tk.StringVar(value='growth');self.finalcheck=tk.BooleanVar()
        self.status=tk.StringVar(value=tr('先读取存档。推荐先查漏，再准备NG+目标栏位。'))
        self.save=None;self.candidate=None;self.busy=False;self.events=queue.Queue();self.buttons=[]
        header=tk.Frame(self,bg='#182b38',padx=26,pady=18);header.pack(fill='x')
        tk.Label(header,text=tr('鬼武者  /  周目继承助手'),font=(self.ui_font,22,'bold'),bg='#182b38',fg='#ffffff').pack(side='left')
        language_panel=tk.Frame(header,bg='#182b38');language_panel.pack(side='right')
        self.language_choice=tk.StringVar(value=next(k for k,v in i18n.LANGUAGES.items() if v==language))
        language_combo=ttk.Combobox(language_panel,textvariable=self.language_choice,values=list(i18n.LANGUAGES),state='readonly',width=14)
        language_combo.pack(anchor='e')
        language_combo.bind('<<ComboboxSelected>>',self.change_language)
        tk.Label(language_panel,text=tr('STEAM  ·  离线处理  ·  自动备份'),font=(self.ui_font,9),bg='#182b38',fg='#a8c9c8').pack(anchor='e',pady=(4,0))
        ttk.Label(self,textvariable=self.status,background='#e4ecef',foreground='#526776',padding=(24,10),wraplength=910).pack(side='bottom',fill='x')
        viewport=ttk.Frame(self,style='Page.TFrame');viewport.pack(fill='both',expand=True)
        canvas=tk.Canvas(viewport,bg='#eef2f5',highlightthickness=0)
        page_scroll=ttk.Scrollbar(viewport,command=canvas.yview)
        canvas.configure(yscrollcommand=page_scroll.set)
        page_scroll.pack(side='right',fill='y');canvas.pack(side='left',fill='both',expand=True)
        frame=ttk.Frame(canvas,padding=(24,18),style='Page.TFrame')
        page=canvas.create_window((0,0),window=frame,anchor='nw')
        frame.bind('<Configure>',lambda e:canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.bind('<Configure>',lambda e:canvas.itemconfigure(page,width=e.width))
        def wheel(event):
            if event.widget.winfo_toplevel()!=self or isinstance(event.widget,(tk.Text,ttk.Combobox)):return
            if frame.winfo_height()>canvas.winfo_height():canvas.yview_scroll(-int(event.delta/120),'units')
        self.bind_all('<MouseWheel>',wheel,add='+')
        def card(title):
            box=ttk.Frame(frame,padding=(18,14));box.pack(fill='x',pady=(0,12))
            ttk.Label(box,text=title,style='Title.TLabel').pack(anchor='w',pady=(0,12))
            return box
        files_card=card(tr('01   选择存档'))
        files=ttk.Frame(files_card);files.pack(fill='x')
        self.filecombo=ttk.Combobox(files,textvariable=self.path_display,state='readonly',width=30);self.filecombo.grid(row=0,column=0,columnspan=3,sticky='ew')
        self.button(files,tr('浏览…'),self.browse).grid(row=0,column=3,padx=5)
        self.button(files,tr('自动寻找'),self.find).grid(row=0,column=4)
        ttk.Label(files,text='SteamID64').grid(row=1,column=0,sticky='w')
        self.sid_entry=ttk.Entry(files,textvariable=self.sid,width=24,show='•');self.sid_entry.grid(row=1,column=1,sticky='w')
        self.privacy_button=self.button(files,tr('显示隐私信息'),self.toggle_privacy)
        self.privacy_button.grid(row=1,column=2,padx=5,sticky='w')
        ttk.Label(files,text=tr('默认隐藏账号和路径个人信息；系统文件选择窗口不受保护。手动编辑路径请先显示。'),style='Muted.TLabel',wraplength=850).grid(row=2,column=0,columnspan=5,sticky='w')
        self.button(files,tr('读取 / 重新读取'),self.read,'Accent.TButton').grid(row=1,column=3,columnspan=2,sticky='ew',pady=8)
        files.columnconfigure(2,weight=1)
        select=ttk.Frame(files_card);select.pack(fill='x',pady=(4,0))
        select.columnconfigure((1,3),weight=1)
        ttk.Label(select,text=tr('来源')).grid(row=0,column=0,padx=(0,10))
        self.srccombo=ttk.Combobox(select,textvariable=self.source,state='readonly',width=25);self.srccombo.grid(row=0,column=1,sticky='ew')
        ttk.Label(select,text=tr('  →  目标')).grid(row=0,column=2,padx=10)
        self.dstcombo=ttk.Combobox(select,textvariable=self.target,state='readonly',width=25);self.dstcombo.grid(row=0,column=3,sticky='ew')
        self.details=ttk.Label(files_card,text='',style='Muted.TLabel',wraplength=860);self.details.pack(anchor='w',pady=(6,0))
        check=card(tr('02   宝箱查漏   ·   推荐先做，可跳过'))
        ttk.Label(check,text=tr('检查 111 个已收录的不刷新宝箱。\n补齐并保存后，请重新读取来源存档。'),style='Muted.TLabel').pack(side='left')
        self.button(check,tr('检查来源宝箱'),self.chests).pack(side='right')
        modes=card(tr('03   选择继承方式'))
        choices=ttk.Frame(modes);choices.pack(fill='x')
        choices.columnconfigure((0,1),weight=1,uniform='choice')
        self.choice_widgets={}
        for col,value,title,description in [(0,'growth',tr('仅继承养成'),tr('复制数值强化与红魂\n保留目标剧情，继续体验新周目')),(1,'finale',tr('同步最终战前'),tr('补齐鬼杀外观、再战资格及商店库存\n素材补偿：力石 53 / 鬼石 55'))]:
            border=tk.Frame(choices,bg='#dce4ea',padx=1,pady=1);border.grid(row=0,column=col,sticky='nsew',padx=(0,6) if col==0 else (6,0))
            box=tk.Frame(border,padx=14,pady=10);box.pack(fill='both',expand=True)
            radio=ttk.Radiobutton(box,text=title,variable=self.mode,value=value,style=value+'.Choice.TRadiobutton');radio.pack(anchor='w')
            label=tk.Label(box,text=description,font=(self.ui_font,10),justify='left',anchor='w',fg='#647586',padx=0,pady=4);label.pack(anchor='w')
            box.bind('<Configure>',lambda e,w=label:w.configure(wraplength=max(150,e.width-28)))
            for widget in (border,box,label):widget.bind('<Button-1>',lambda e,v=value:self.mode.set(v))
            self.choice_widgets[value]=(border,box,label)
        self.confirm=ttk.Checkbutton(modes,text=tr('我确认：来源已通关，并回到最后两段连续主线之前（非天守内中途存档）'),variable=self.finalcheck,style='Modern.TCheckbutton')
        style.configure('Modern.TCheckbutton',wraplength=820)
        self.confirm.pack(anchor='w',pady=(12,0))
        self.confirm_hint=ttk.Label(modes,style='Muted.TLabel');self.confirm_hint.pack(anchor='w',padx=4,pady=(2,8))
        ttk.Label(modes,text=tr('目标须为鬼杀 NG+。同步将替换目标剧情与背包，保留再战成绩；共享外观影响全部栏位。'),style='Muted.TLabel',wraplength=850).pack(anchor='w')
        ttk.Label(modes,text=tr('补齐最终连战前16项鬼杀再战资格；弁庆（武器解放）与最终源义经不提前解锁，已有资格不撤销'),style='Muted.TLabel',wraplength=850).pack(anchor='w',pady=(4,0))
        preview_card=card(tr('04   预览与应用'))
        toolbar=ttk.Frame(preview_card);toolbar.pack(fill='x',pady=(0,12))
        self.button(toolbar,tr('生成修改预览'),self.preview,'Accent.TButton').pack(side='left')
        self.button(toolbar,tr('校验并写回'),lambda:self.commit(False)).pack(side='left',padx=6)
        self.button(toolbar,tr('校验并另存'),lambda:self.commit(True)).pack(side='left')
        self.button(toolbar,tr('恢复备份…'),self.restore).pack(side='right')
        logframe=ttk.Frame(preview_card);logframe.pack(fill='both',expand=True)
        self.log=tk.Text(logframe,height=6,wrap='word',background='#f5f8fa',foreground='#334b5b',relief='flat',padx=16,pady=12,spacing1=3,spacing3=3)
        scrollbar=ttk.Scrollbar(logframe,command=self.log.yview)
        self.log.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side='right',fill='y');self.log.pack(fill='both',expand=True)
        for var in (self.source,self.target,self.mode,self.finalcheck,self.path,self.sid):
            var.trace_add('write',self.invalidate)
        self.mode.trace_add('write',self.update_mode)
        self.source.trace_add('write',self.reset_confirmation)
        self.path.trace_add('write',self.reset_confirmation)
        self.sid.trace_add('write',self.reset_confirmation)
        self.update_mode()
        self.show(tr('尚未生成预览\n先读取存档、检查来源收集，再选择继承方式。所有修改会先展示预览，并在写入前备份。'))
        self.filecombo.bind('<<ComboboxSelected>>',self.select_path)
        self.path.trace_add('write',self.refresh_privacy)
        self.sid.trace_add('write',self.refresh_privacy)
        self.path_display.trace_add('write',self.edit_path)
        self.protocol('WM_DELETE_WINDOW',self.close)
        self.poll_id=self.after(100,self.poll)
        if initial:
            self.path.set(initial[0]);self.sid.set(initial[1])
        self.find()

    def change_language(self,event=None):
        requested=i18n.LANGUAGES[self.language_choice.get()]
        if requested==i18n.language:return
        if self.busy or (self.save and not messagebox.askyesno(tr('切换语言'),tr('切换语言将重建界面并清除当前预览，需要重新读取存档。不会写入游戏文件。继续？'),parent=self)):
            self.language_choice.set(next(k for k,v in i18n.LANGUAGES.items() if v==i18n.language))
            return
        self.next_language=requested
        self.next_initial=(self.path.get(),self.sid.get())
        self.close()

    def button(self,parent,text,command,style='TButton'):
        b=ttk.Button(parent,text=text,style=style,command=lambda:self.safe(command));self.buttons.append(b);return b

    def private_text(self,text):
        if self.revealed:return str(text)
        return privacy.redact(text,(self.sid.get().strip(),getattr(self,'loaded_sid','')))

    def refresh_privacy(self,*_):
        self.syncing_path=True
        try:
            self.path_display.set(self.private_text(self.path.get()))
            self.filecombo['values']=[f'{i+1} | {self.private_text(p)}' for i,p in enumerate(self.discovered_paths)]
        finally:self.syncing_path=False
        self.show(self.log_raw)

    def toggle_privacy(self):
        self.revealed=not self.revealed
        self.sid_entry.configure(show='' if self.revealed else '•')
        self.filecombo.configure(state='normal' if self.revealed else 'readonly')
        self.privacy_button.configure(text=tr('隐藏隐私信息') if self.revealed else tr('显示隐私信息'))
        self.refresh_privacy()

    def edit_path(self,*_):
        if self.revealed and not self.syncing_path:
            # Combobox selection contains an index; the selection handler maps it
            # to the original path. Never send a masked/display string to core.
            if self.path_display.get() not in self.filecombo['values']:
                self.path.set(self.path_display.get())

    def select_path(self,event=None):
        index=self.filecombo.current()
        if 0<=index<len(self.discovered_paths):
            path=self.discovered_paths[index]
            self.path.set(path);self.sid.set(core.steam_id(path))

    def reset_confirmation(self,*_):
        self.finalcheck.set(False)

    def update_mode(self,*_):
        finale=self.mode.get()=='finale'
        self.finalcheck.set(False)
        self.confirm.configure(state='normal' if finale else 'disabled')
        self.confirm_hint.configure(text=tr('需人工确认位置；工具仅检查通关标记，不会自动确认上述位置。') if finale else tr('仅继承养成不需要确认最终战前位置；此选项已禁用。'))
        style=ttk.Style(self)
        for value,(border,box,label) in self.choice_widgets.items():
            selected=self.mode.get()==value
            bg='#edf7f4' if selected else '#f7f9fb'
            border.configure(bg='#168577' if selected else '#dce4ea')
            box.configure(bg=bg);label.configure(bg=bg)
            style.configure(value+'.Choice.TRadiobutton',background=bg,foreground='#12675c' if selected else '#263747')
            style.map(value+'.Choice.TRadiobutton',background=[('active',bg)])

    def safe(self,fn):
        if self.busy:return
        try:fn()
        except Exception as e:messagebox.showerror(tr('无法完成'),self.private_text(e),parent=self)

    def invalidate(self,*_):
        self.candidate=None
        if self.save:
            try:
                s=self.save.info(self.slot(self.source));t=self.save.info(self.slot(self.target))
                self.details.configure(text=tr('来源：{v0}\n目标：{v1}',v0=s['detail'],v1=t['detail']))
            except Exception:pass

    def show(self,text):
        self.log_raw=str(text)
        self.log.delete('1.0','end');self.log.insert('end',self.private_text(text))

    def run(self,fn,done,status):
        self.busy=True;self.status.set(status)
        for b in self.buttons:b.configure(state='disabled')
        def worker():
            try:self.events.put((True,fn(),done))
            except Exception as e:self.events.put((False,str(e),done))
        threading.Thread(target=worker,daemon=True).start()

    def poll(self):
        try:
            ok,value,done=self.events.get_nowait();self.busy=False
            for b in self.buttons:b.configure(state='normal')
            if ok:
                try:done(value)
                except Exception as e:messagebox.showerror(tr('无法完成'),self.private_text(e),parent=self)
            else:
                self.status.set(tr('操作未完成；请检查错误说明。'))
                messagebox.showerror(tr('无法完成'),self.private_text(value),parent=self)
        except queue.Empty:pass
        self.poll_id=self.after(100,self.poll)

    def close(self):
        if self.busy:
            messagebox.showinfo(tr('处理中'),tr('请等待当前校验或写入完成。'),parent=self);return
        self.after_cancel(self.poll_id)
        self.destroy()

    def find(self):
        paths=[str(p) for p in core.discover()];self.discovered_paths=paths
        self.refresh_privacy()
        if len(paths)==1 and not self.path.get():
            self.path.set(paths[0]);self.sid.set(core.steam_id(paths[0]))
        if len(paths)>1:self.status.set(tr('发现多个账号存档，请在路径下拉框明确选择自己的文件；不会默认选择首个账号。'))
        if not paths:self.status.set(tr('未自动找到存档，请浏览选择 data001Slot.bin 并填写SteamID64。'))

    def browse(self):
        p=filedialog.askopenfilename(title=tr('选择 data001Slot.bin'),filetypes=[(tr('游戏存档'),'*.bin'),(tr('所有文件'),'*.*')])
        if p:self.path.set(p);self.sid.set(core.steam_id(p))

    def read(self):
        path=Path(self.path.get());sid=self.sid.get().strip()
        core.ensure_closed()
        encrypted=path.read_bytes()
        def done(save):
            self.save=save;self.loaded_path=path.resolve();self.loaded_sid=sid;self.loaded_bytes=encrypted
            values=[]
            for i in range(10):
                x=save.info(i)
                values.append(f"{i+1} | {x['title'] if x['occupied'] else tr('空栏位')}")
            self.srccombo['values']=values;self.dstcombo['values']=values
            self.source.set(values[0]);self.target.set(values[1]);self.candidate=None
            self.show(tr('读取成功。\n\n建议先检查来源宝箱；补齐后重新保存、退出游戏并点击“重新读取”。\n\n选择两个不同的已有手动栏位，然后生成修改预览。'))
            self.status.set(tr('已读取10个手动栏位；自动存档不会修改。'))
        self.run(lambda:core.Save(core.crypto(encrypted,sid,'d')),done,tr('正在解密并检查存档结构…'))

    def current(self):
        if not self.save:raise ValueError(tr('请先读取存档'))
        if Path(self.path.get()).resolve()!=self.loaded_path or self.sid.get().strip()!=self.loaded_sid:
            raise ValueError(tr('文件或账号已更改，请重新读取'))
        if self.loaded_path.read_bytes()!=self.loaded_bytes:
            raise ValueError(tr('存档已变化，请重新读取最新文件'))

    def slot(self,var):return int(var.get().split('|')[0].strip())-1

    def chests(self):
        self.current();rows=self.save.chests(self.slot(self.source))
        win=tk.Toplevel(self);win.title(tr('来源不刷新宝箱查漏'));win.geometry('1100x650')
        missing=[r for r in rows if r['state']==0]
        unknown=sum(r['state'] not in (0,15) for r in rows)
        ttk.Label(win,text=tr('已收录不刷新宝箱 {v0} 处：{v1} 处未开启，{v2} 处状态未知。双击条目打开地图。',v0=len(rows),v1=len(missing),v2=unknown),padding=12).pack(anchor='w')
        ttk.Label(win,text=tr('排除最终战区域3箱；未开启可能需要先完成任务或藏宝图条件，不代表现在就能领取。'),padding=8).pack(anchor='w')
        ttk.Label(win,text=tr('完成补漏后：游戏内保存 → 退出游戏 → 重新读取来源。地图需要网络，存档不上传。'),padding=10).pack(side='bottom',anchor='w')
        ttk.Label(win,text=tr('物品与具名地区采用游戏内译名；地图区域编号不是官方地名。选择条目可核对英文原名。'),wraplength=1040,padding=8).pack(anchor='w')
        original=tk.StringVar(value='')
        ttk.Label(win,textvariable=original,wraplength=1040,padding=10).pack(side='bottom',fill='x')
        container=ttk.Frame(win);container.pack(fill='both',expand=True,padx=10,pady=8)
        tree=ttk.Treeview(container,columns=('area','contents','status'),show='headings')
        for key,title,width in [('area',tr('地区 / 宝箱'),400),('contents',tr('内容'),430),('status',tr('状态'),180)]:
            tree.heading(key,text=title);tree.column(key,width=width)
        scroll=ttk.Scrollbar(container,command=tree.yview);tree.configure(yscrollcommand=scroll.set)
        scroll.pack(side='right',fill='y');tree.pack(fill='both',expand=True)
        for i,r in enumerate(sorted(rows,key=lambda r:(r['state']!=0,r['stage'],r['id']))):
            tree.insert('', 'end',iid=r['id'],values=(chest_labels.label(r['area'])+' / '+r['id'],chest_labels.contents(r['contents']),r['status']))
        byid={r['id']:r for r in rows}
        def selected(event):
            sel=tree.selection()
            if sel:
                r=byid[sel[0]]
                original.set(tr('英文原名：{v0}\n内容：{v1}',v0=r['area'],v1=r['contents']))
        tree.bind('<<TreeviewSelect>>',selected)
        def locate(event):
            sel=tree.selection()
            if sel:
                r=byid[sel[0]];webbrowser.open(r['url'])
        tree.bind('<Double-1>',locate)

    def signature(self):
        return (self.path.get(),self.sid.get(),self.source.get(),self.target.get(),self.mode.get(),self.finalcheck.get())

    def preview(self):
        self.current()
        source,target=self.slot(self.source),self.slot(self.target)
        mode,confirmed=self.mode.get(),self.finalcheck.get();sig=self.signature()
        save=self.save
        def done(result):
            if sig!=self.signature():
                self.status.set(tr('选项已变化，请重新生成预览。'));return
            self.candidate=result;self.preview_signature=sig
            _,report=result
            scope=(tr('\n\n仅复制目标手动栏位的数值强化与红魂；不修改剧情、背包、再战资格或共享外观。\n自动存档、来源及其余手动栏位保留。写回前还将进行加密回读校验。') if mode=='growth' else
                   tr('\n\n只修改目标手动栏位及明确列出的共享外观。\n自动存档、来源及其余手动栏位保留。写回前还将进行加密回读校验。'))
            self.show(tr('来源 {v0}号 → 目标 {v1}号\n\n',v0=source + 1,v1=target + 1)+'\n'.join('• '+c for c in report['changes'])+scope)
            self.status.set(tr('预览已生成。检查内容后选择写回或另存。'))
        self.run(lambda:save.plan(source,target,mode,confirmed),done,tr('正在生成候选并核对修改范围…'))

    def commit(self,save_as):
        self.current()
        if not self.candidate or self.preview_signature!=self.signature():raise ValueError(tr('请先生成当前选项的预览'))
        output=self.loaded_path
        if save_as:
            p=filedialog.asksaveasfilename(title=tr('另存加密存档'),initialfile='data001Slot.bin',defaultextension='.bin')
            if not p:return
            output=Path(p).resolve()
        if not messagebox.askyesno(tr('确认应用'),tr('将修改预览中的内容写入：\n{v0}\n\n现有文件会先备份。是否继续？',v0=self.private_text(output)),parent=self):return
        expected=output.read_bytes() if output.exists() else None
        candidate,report=self.candidate;sid=self.loaded_sid
        original_path,original=self.loaded_path,self.loaded_bytes
        def work():
            core.ensure_closed()
            encrypted=core.crypto(candidate,sid,'e')
            if core.crypto(encrypted,sid,'d')!=candidate:raise ValueError(tr('加密回读不一致，未写入'))
            if original_path.read_bytes()!=original:raise ValueError(tr('原存档已变化，请重新读取'))
            backup=core.write_transaction(output,encrypted,expected,dict(report,encrypted_sha256=core.sha(encrypted)))
            return backup
        def done(backup):
            self.candidate=None;self.save=None
            self.show(tr('写入与加密回读校验完成。\n\n输出：{v0}\n备份/记录：{v1}\n\n进入游戏后，从指定手动栏位读取。重新保存后，选档界面的任务摘要会更新。\nSteam云存档若提示冲突，请保留此次修改的本地文件。',v0=output,v1=backup))
            self.status.set(tr('完成。继续操作前请重新读取存档。'))
        self.run(work,done,tr('正在加密、回读验证并备份写入…'))

    def restore(self):
        self.current()
        p=filedialog.askopenfilename(title=tr('选择此前备份的加密存档'),initialdir=self.loaded_path.parent/'OnimushaEditor_Backups',filetypes=[(tr('存档备份'),'*.bin')])
        if not p:return
        if not messagebox.askyesno(tr('恢复整份文件'),tr('恢复将还原这份备份中的所有栏位与共享数据。当前文件会先备份。继续？'),parent=self):return
        blob=Path(p).read_bytes();sid=self.loaded_sid;dest=self.loaded_path;expected=self.loaded_bytes
        def work():
            core.Save(core.crypto(blob,sid,'d'))
            return core.write_transaction(dest,blob,expected,{'operation':'restore','restored_sha256':core.sha(blob)})
        def done(backup):
            self.save=None;self.candidate=None;self.show(tr('恢复完成。恢复前文件备份于：\n{v0}',v0=backup))
            self.status.set(tr('恢复完成，请重新读取。'))
        self.run(work,done,tr('正在验证备份并恢复…'))


if __name__=='__main__':
    language='zh';initial=None
    while True:
        app=App(language,initial);app.mainloop()
        if not app.next_language:break
        language,initial=app.next_language,app.next_initial
