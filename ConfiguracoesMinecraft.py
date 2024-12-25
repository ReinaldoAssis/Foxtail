import os
from pathlib import Path
import platform
import queue
import shutil
import signal
import subprocess
from threading import Thread
import threading
import tkinter as tk
from tkinter import Tk, filedialog
from tkinter import ttk
from tkinter import scrolledtext
from tkinter import messagebox

class ConfiguracoesMinecraft:
    def __init__(self, master):
        self.master = master
        self.window = None
        self.db = master.db
        self.default_config = {
            'launcher_status': 'Pendente',
            'modpack_status': 'Pendente',
            'player_nickname': '',
            'player_skin_url': '',
            'launcher_path': str(Path.home() / 'minecraft_launcher'),
            'modpack_path': str(Path.home() / 'minecraft_modpack')
        }
        self.load_config()

    def load_config(self):
        config_table = self.db.table('minecraft_settings')
        stored_config = config_table.get(doc_id=1)
        
        if stored_config:
            self.config = stored_config
        else:
            self.config = self.default_config
            config_table.insert(self.default_config)

    def save_config(self):
        config_table = self.db.table('minecraft_settings')
        if config_table.get(doc_id=1):
            config_table.update(self.config, doc_ids=[1])
        else:
            config_table.insert(self.config)

    def download_files(self, url, path, status_key, status_label):
        try:
            # Placeholder para download real
            # Em produção, usar requests ou outro método apropriado
            os.makedirs(path, exist_ok=True)
            
            # Simulando download
            status_label.config(text="Baixando...")
            self.window.update()
            
            # Aqui você colocaria o código real de download
            # Por enquanto, apenas criamos um arquivo de teste
            with open(os.path.join(path, 'test.txt'), 'w') as f:
                f.write('Test file')
            
            self.config[status_key] = 'OK'
            status_label.config(text="OK", foreground="green")
            
        except Exception as e:
            self.config[status_key] = 'Pendente'
            status_label.config(text="Pendente", foreground="red")
            messagebox.showerror("Erro", f"Erro ao baixar arquivos: {str(e)}")
        
        self.save_config()

    def delete_instance(self, path, status_key, status_label):
        if messagebox.askyesno("Confirmar", "Tem certeza que deseja deletar esta instância?"):
            try:
                if os.path.exists(path):
                    shutil.rmtree(path)
                self.config[status_key] = 'Pendente'
                status_label.config(text="Pendente", foreground="red")
                self.save_config()
                messagebox.showinfo("Sucesso", "Instância deletada com sucesso!")
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao deletar instância: {str(e)}")

    def save_player_settings(self):
        self.config['player_nickname'] = self.nickname_entry.get()
        self.config['player_skin_url'] = self.skin_url_entry.get()
        self.save_config()
        messagebox.showinfo("Sucesso", "Configurações do jogador salvas com sucesso!")

    def activate(self):
        if self.window:
            self.window.lift()
            return

        self.window = tk.Toplevel(self.master)
        self.window.title("Configurações Minecraft")
        self.window.geometry("500x400")

        # Criar notebook para as tabs
        notebook = ttk.Notebook(self.window)
        notebook.pack(expand=True, fill='both', padx=10, pady=5)

        # Tab Launcher
        launcher_frame = ttk.Frame(notebook, padding=10)
        notebook.add(launcher_frame, text='Launcher')

        # Status do Launcher
        launcher_status_label = ttk.Label(launcher_frame, text="Status:")
        launcher_status_label.grid(row=0, column=0, sticky=tk.W, pady=5)
        
        self.launcher_status = ttk.Label(
            launcher_frame, 
            text=self.config['launcher_status'],
            foreground="green" if self.config['launcher_status'] == 'OK' else "red"
        )
        self.launcher_status.grid(row=0, column=1, sticky=tk.W, pady=5)

        # Botões do Launcher
        launcher_buttons_frame = ttk.Frame(launcher_frame)
        launcher_buttons_frame.grid(row=1, column=0, columnspan=2, pady=10)

        ttk.Button(
            launcher_buttons_frame,
            text="Download",
            command=lambda: threading.Thread(
                target=self.download_files,
                args=("https://github.com/placeholder/launcher", 
                      self.config['launcher_path'],
                      'launcher_status',
                      self.launcher_status)
            ).start()
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            launcher_buttons_frame,
            text="Deletar Instância",
            style="Delete.TButton",
            command=lambda: self.delete_instance(
                self.config['launcher_path'],
                'launcher_status',
                self.launcher_status
            )
        ).pack(side=tk.LEFT, padx=5)

        # Tab Modpack
        modpack_frame = ttk.Frame(notebook, padding=10)
        notebook.add(modpack_frame, text='Modpack')

        # Status do Modpack
        modpack_status_label = ttk.Label(modpack_frame, text="Status:")
        modpack_status_label.grid(row=0, column=0, sticky=tk.W, pady=5)
        
        self.modpack_status = ttk.Label(
            modpack_frame, 
            text=self.config['modpack_status'],
            foreground="green" if self.config['modpack_status'] == 'OK' else "red"
        )
        self.modpack_status.grid(row=0, column=1, sticky=tk.W, pady=5)

        # Botões do Modpack
        modpack_buttons_frame = ttk.Frame(modpack_frame)
        modpack_buttons_frame.grid(row=1, column=0, columnspan=2, pady=10)

        ttk.Button(
            modpack_buttons_frame,
            text="Download",
            command=lambda: threading.Thread(
                target=self.download_files,
                args=("https://github.com/placeholder/modpack",
                      self.config['modpack_path'],
                      'modpack_status',
                      self.modpack_status)
            ).start()
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            modpack_buttons_frame,
            text="Deletar Instância",
            style="Delete.TButton",
            command=lambda: self.delete_instance(
                self.config['modpack_path'],
                'modpack_status',
                self.modpack_status
            )
        ).pack(side=tk.LEFT, padx=5)

        # Tab Jogador
        player_frame = ttk.Frame(notebook, padding=10)
        notebook.add(player_frame, text='Jogador')

        # Nickname
        ttk.Label(player_frame, text="Nickname:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.nickname_entry = ttk.Entry(player_frame, width=40)
        self.nickname_entry.insert(0, self.config['player_nickname'])
        self.nickname_entry.grid(row=0, column=1, sticky=tk.W, pady=5)

        # Skin URL
        ttk.Label(player_frame, text="URL da Skin:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.skin_url_entry = ttk.Entry(player_frame, width=40)
        self.skin_url_entry.insert(0, self.config['player_skin_url'])
        self.skin_url_entry.grid(row=1, column=1, sticky=tk.W, pady=5)

        # Botão Salvar
        ttk.Button(
            player_frame,
            text="Salvar",
            command=self.save_player_settings
        ).grid(row=2, column=0, columnspan=2, pady=20)

        # Estilo para botão vermelho
        style = ttk.Style()
        style.configure("Delete.TButton", foreground="red")

        return self

    def on_closing(self):
        self.window.destroy()
        self.window = None