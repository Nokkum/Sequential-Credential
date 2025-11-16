import subprocess
import os
from tkinter import messagebox


class BotLauncher:
    BOT_FILE = 'main.py'

    def launch(self, token: str):
        if not os.path.exists(self.BOT_FILE):
            messagebox.showerror('Error', f'Cannot find {self.BOT_FILE}')
            return
        try:
            env = os.environ.copy()
            env['DISCORD_TOKEN'] = token
            subprocess.Popen(['python', self.BOT_FILE], env=env)
            messagebox.showinfo('Bot', 'Discord bot launched')
        except Exception as e:
            messagebox.showerror('Error', f'Failed to launch bot: {e}')