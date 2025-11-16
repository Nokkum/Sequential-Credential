import os
import base64
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
from core.security import EncryptionManager
from core.configs import ConfigManager
from core.launch import BotLauncher
from core.database import Database
from core.migration import migrate_filesystem_to_db
from core.clipboard import secure_copy

class MasterPasswordDialog(simpledialog.Dialog):
    def body(self, master):
        ttk.Label(master, text='Enter master password (or leave blank to use MASTER_PASSWORD env var):').grid(row=0)
        self.pw_var = tk.StringVar()
        self.entry = ttk.Entry(master, textvariable=self.pw_var, show='*', width=40)
        self.entry.grid(row=1)
        return self.entry

    def apply(self):
        self.result = self.pw_var.get()


class CredentialGUI:
    def __init__(self):
        # prompt for master password via GUI dialog
        root = tk.Tk()
        root.withdraw()  # hide main while we ask for password
        dlg = MasterPasswordDialog(root, title='Master Password')
        master_password = dlg.result or os.environ.get('MASTER_PASSWORD')
        root.destroy()

        # initialize core services
        self.db = Database()
        self.encryption = EncryptionManager(master_password)
        self.cfg = ConfigManager(self.db, self.encryption)
        self.launcher = BotLauncher()

        # build main window
        self.root = tk.Tk()
        self.root.title('Sequential Credential Manager')
        self.root.geometry('520x620')
        self.root.resizable(False, False)

        self.category_var = tk.StringVar(value='tokens')
        self.provider_var = tk.StringVar(value='Discord')
        self.config_var = tk.StringVar(value='default')
        self.data_var = tk.StringVar()
        self.store_in_db = tk.BooleanVar(value=False)
        self.show_data = tk.BooleanVar(value=False)

        self.build_ui()
        self.refresh_configs()
        self.root.mainloop()

    def build_ui(self):
        frame = ttk.Frame(self.root, padding=12)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text='Select Type:', font=('Segoe UI', 10, 'bold')).grid(row=0, column=0, sticky='w')
        ttk.Combobox(frame, textvariable=self.category_var, values=['tokens', 'apis'], state='readonly').grid(row=1, column=0, sticky='we')

        ttk.Label(frame, text='Select Provider:', font=('Segoe UI', 10, 'bold')).grid(row=2, column=0, sticky='w')
        ttk.Combobox(frame, textvariable=self.provider_var, values=['Discord', 'OpenAI', 'Google', 'GitHub', 'Slack', 'Handler', 'Other'], state='readonly').grid(row=3, column=0, sticky='we')

        ttk.Label(frame, text='Configuration:', font=('Segoe UI', 10, 'bold')).grid(row=4, column=0, sticky='w')
        self.config_dropdown = ttk.Combobox(frame, textvariable=self.config_var, state='readonly')
        self.config_dropdown.grid(row=5, column=0, sticky='we')

        ttk.Label(frame, text='Token / API Key:', font=('Segoe UI', 10, 'bold')).grid(row=6, column=0, sticky='w')
        self.data_entry = ttk.Entry(frame, textvariable=self.data_var, width=60, show='*')
        self.data_entry.grid(row=7, column=0, sticky='we')

        self.toggle_btn = ttk.Button(frame, text='Show', command=self.toggle_visibility)
        self.toggle_btn.grid(row=8, column=0, pady=6, sticky='w')

        ttk.Checkbutton(frame, text='Store encrypted blob in DB (instead of filesystem)', variable=self.store_in_db).grid(row=9, column=0, sticky='w')

        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=10, column=0, pady=8)

        ttk.Button(btn_frame, text='Save / Update', command=self.on_save).grid(row=0, column=0, padx=4)
        ttk.Button(btn_frame, text='Delete', command=self.on_delete).grid(row=0, column=1, padx=4)
        ttk.Button(btn_frame, text='Launch Discord Bot', command=self.on_launch).grid(row=0, column=2, padx=4)
        ttk.Button(btn_frame, text='Export Configurations', command=self.export_configs).grid(row=0, column=3, padx=4)
        ttk.Button(btn_frame, text='Import Configurations', command=self.import_configs).grid(row=0, column=4, padx=4)

        migrate_frame = ttk.Frame(frame)
        migrate_frame.grid(row=11, column=0, pady=6, sticky='we')
        ttk.Button(migrate_frame, text='Migrate filesystem → DB', command=self.migrate_filesystem).grid(row=0, column=0)

        self.category_var.trace('w', lambda *_: self.refresh_configs())
        self.provider_var.trace('w', lambda *_: self.refresh_configs())
        self.config_dropdown.bind('<<ComboboxSelected>>', lambda *_: self.load_selected())

    def toggle_visibility(self):
        if self.show_data.get():
            self.data_entry.config(show='*')
            self.toggle_btn.config(text='Show')
        else:
            self.data_entry.config(show='')
            self.toggle_btn.config(text='Hide')
        self.show_data.set(not self.show_data.get())

    def refresh_configs(self):
        configs = self.cfg.list_configs(self.category_var.get(), self.provider_var.get())
        self.config_dropdown['values'] = configs
        if configs:
            self.config_var.set(configs[0])
            self.load_selected()
        else:
            self.config_var.set('default')
            self.data_var.set('')

    def load_selected(self):
        cat = self.category_var.get(); prov = self.provider_var.get(); cfg = self.config_var.get()
        # attempt to get blob entry first
        blob_entry = self.db.get_blob_entry(cat, prov, cfg)
        if blob_entry and blob_entry.get('blob'):
            try:
                data = self.encryption.decrypt(base64.b64decode(blob_entry['blob']))
                self.data_var.set(data)
                return
            except Exception:
                pass
        # fallback to filesystem
        token = self.cfg.load_from_filesystem(cat, prov, cfg)
        self.data_var.set(token or '')

    def on_save(self):
        value = self.data_var.get().strip()
        cfg = self.config_var.get().strip()
        if not value or not cfg:
            messagebox.showwarning('Missing', 'Provide a token and config name')
            return
        encrypted = self.encryption.encrypt(value)
        if self.store_in_db.get():
            blob = base64.b64encode(encrypted).decode('utf-8')
            meta = {'blob': blob}
            self.db.set_blob(self.category_var.get(), self.provider_var.get(), cfg, meta)
            # also mirror minimal metadata
            self.db.set(self.category_var.get(), f"{self.provider_var.get()}_{cfg}", {'stored': 'db_blob'})
        else:
            path_meta = self.cfg.save_to_filesystem(self.category_var.get(), self.provider_var.get(), cfg, encrypted)
            self.db.set(self.category_var.get(), f"{self.provider_var.get()}_{cfg}", path_meta)
        messagebox.showinfo('Saved', f'Saved {cfg}')
        self.refresh_configs()

    def on_delete(self):
        cfg = self.config_var.get()
        if messagebox.askyesno('Confirm', f'Delete {cfg}?'):
            self.db.delete(self.category_var.get(), f"{self.provider_var.get()}_{cfg}")
            self.cfg.delete_filesystem(self.category_var.get(), self.provider_var.get(), cfg)
            messagebox.showinfo('Deleted', f'Deleted {cfg}')
            self.refresh_configs()

    def on_launch(self):
        token = self.data_var.get().strip()
        if not token:
            messagebox.showwarning('Missing Token', 'Please provide a Discord bot token')
            return
        self.launcher.launch(token)

    def export_configs(self):
        data = self.db.export_provider(self.category_var.get(), self.provider_var.get())
        if not data:
            messagebox.showinfo('Export', 'No configurations found')
            return
        file_path = filedialog.asksaveasfilename(defaultextension='.seqcfg')
        if not file_path:
            return
        self.db.export_to_file(data, file_path)
        messagebox.showinfo('Export', 'Export complete')

    def import_configs(self):
        file_path = filedialog.askopenfilename(filetypes=[('Sequential Config','*.seqcfg')])
        if not file_path:
            return
        self.db.import_from_file(file_path)
        messagebox.showinfo('Import', 'Import complete')
        self.refresh_configs()

    def migrate_filesystem(self):
        migrated = migrate_filesystem_to_db(self.db, self.cfg)
        messagebox.showinfo('Migrate', f'Migrated {migrated} entries from filesystem to DB')
        self.refresh_configs()