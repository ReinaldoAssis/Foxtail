import tkinter as tk
from tinydb import TinyDB
import importlib.util
from PIL import Image, ImageTk
from tkinter import ttk, filedialog, scrolledtext, messagebox
import json
import subprocess
import os
import platform
import signal
from threading import Thread
import queue

import shutil
import requests
from pathlib import Path
import threading

# Estou mantendo tudo em um arquivo só porque ainda não sei como vai ser para fazer o executavel, então
# para evitar problemas preferi manter tudo em um lugar só.

# Cada interface (UI) é uma classe, basta copiar uma e colar no claude.ai e descrever a nova interface que você
# quer que ele crie, dado um bom prompt os resultados geralmente são bons. A maioria aqui foi gerado lá, depois
# só ajusto o necessário e implemento a interação global entre as interfaces.

# -----------------

# Arquitetura da UI

# Para o UI, as classes possuem dois metódos importantes: init e activate
# no init passamos o master, a interface principal do programa que contém a nossa instância do banco de dados
# é por essa instância que as demais interfaces possuem acesso ao banco de dados.

# o activate é onde descrevemos a ui em si.

# -----------------

# Arquitetura do servidor

# Aqui ainda não decidi se irei utilizar ngrok ou noip, mas isso muda apenas o backend, para o usuário a experiência
# será a mesma: um botão na interface principal que ao apertar o endereço do server é copiado. Esse tipo de informação
# será salvo diretamente no repositório.

# -----------------

# TODO
# [ ] Criar sistema de autoupdate
#       - Comparar versão atual (var global) com versão existente no json presente no github.
#       - Caso desatualizado, prompt pedindo para atualizar (baixar nova versão e agendar por meio de uma thread
#       - não deamon a exclusão da versão antiga, agendar também para o programa abrir após a exclusão da antiga)

# [ ] Implementar ngrok/noip na configuração do servidor
# [ ] Implementar copiar ip do server ao clicar botão na interface principal
# [ ] Implementar download do launcher (e decidir qual launcher utilizar)
# [ ] Implementar download e configuração do modpack

class ConfiguracoesServidor:
    def __init__(self, master):
        self.master = master
        self.window = None
        self.server_process = None
        self.log_queue = queue.Queue()
        self.db = master.db  # Using master's TinyDB instance
        self.default_config = {
            'server_ip': 'localhost',
            'server_port': '25565',
            'server_name': 'Minecraft Server',
            'jar_path': '',
            'min_ram': '1G',
            'max_ram': '4G'
        }
        self.load_config()

    def load_config(self):
        # Get config from TinyDB, create if doesn't exist
        config_table = self.db.table('minecraft_server')
        stored_config = config_table.get(doc_id=1)
        
        if stored_config:
            self.config = stored_config
        else:
            self.config = self.default_config
            config_table.insert(self.default_config)

    def save_config(self):
        config_table = self.db.table('minecraft_server')
        if config_table.get(doc_id=1):
            config_table.update(self.config, doc_ids=[1])
        else:
            config_table.insert(self.config)

    def select_jar(self):
        filename = filedialog.askopenfilename(
            title="Selecione o arquivo .jar do servidor",
            filetypes=[("JAR files", "*.jar")]
        )
        if filename:
            self.config['jar_path'] = filename
            self.jar_path_entry.delete(0, tk.END)
            self.jar_path_entry.insert(0, filename)
            self.save_config()

    def update_log(self):
        while True:
            try:
                line = self.log_queue.get_nowait()
                self.log_text.insert(tk.END, line)
                self.log_text.see(tk.END)
            except queue.Empty:
                break
        if self.window:
            self.window.after(100, self.update_log)

    def read_output(self, process):
        while True:
            if process.poll() is not None:
                break
            output = process.stdout.readline()
            if output:
                self.log_queue.put(output)

    def start_server(self):
        if self.server_process and self.server_process.poll() is None:
            self.log_queue.put("Servidor já está rodando!\n")
            return

        if not os.path.exists(self.config['jar_path']):
            self.log_queue.put("Arquivo .jar não encontrado!\n")
            return

        java_cmd = [
            'java',
            f'-Xms{self.config["min_ram"]}',
            f'-Xmx{self.config["max_ram"]}',
            '-jar',
            self.config['jar_path'],
            'nogui'
        ]

        try:
            # Get server directory from jar path
            server_dir = os.path.dirname(self.config['jar_path'])
            
            self.server_process = subprocess.Popen(
                java_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                cwd=server_dir,  # Set working directory to server directory
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if platform.system() == 'Windows' else 0
            )
            
            Thread(target=self.read_output, args=(self.server_process,), daemon=True).start()
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            self.log_queue.put("Iniciando servidor...\n")
            
        except Exception as e:
            self.log_queue.put(f"Erro ao iniciar servidor: {str(e)}\n")

    def stop_server(self):
        if not self.server_process or self.server_process.poll() is not None:
            self.log_queue.put("Servidor não está rodando!\n")
            return

        try:
            if platform.system() == 'Windows':
                self.server_process.send_signal(signal.CTRL_BREAK_EVENT)
            else:
                self.server_process.terminate()
            
            self.server_process.wait(timeout=30)
            self.server_process = None
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            self.log_queue.put("Servidor desligado com sucesso!\n")
            
        except Exception as e:
            self.log_queue.put(f"Erro ao desligar servidor: {str(e)}\n")
            if self.server_process:
                self.server_process.kill()

    def save_settings(self):
        self.config['server_ip'] = self.ip_entry.get()
        self.config['server_port'] = self.port_entry.get()
        self.config['server_name'] = self.name_entry.get()
        self.config['min_ram'] = self.min_ram_entry.get()
        self.config['max_ram'] = self.max_ram_entry.get()
        self.save_config()
        self.log_queue.put("Configurações salvas com sucesso!\n")

    def on_closing(self):
        if self.server_process and self.server_process.poll() is None:
            self.log_queue.put("Servidor continuará rodando em segundo plano.\n")
        self.window.destroy()
        self.window = None

    def activate(self):
        if self.window:
            self.window.lift()
            return

        self.window = tk.Toplevel(self.master)
        self.window.title("Configurações do Servidor Minecraft")
        self.window.geometry("600x700")
        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Frame principal
        main_frame = ttk.Frame(self.window, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Configurações básicas
        ttk.Label(main_frame, text="Configurações do Servidor", font=('', 12, 'bold')).grid(row=0, column=0, columnspan=2, pady=10)

        # IP
        ttk.Label(main_frame, text="IP do Servidor:").grid(row=1, column=0, sticky=tk.W)
        self.ip_entry = ttk.Entry(main_frame, width=40)
        self.ip_entry.insert(0, self.config['server_ip'])
        self.ip_entry.grid(row=1, column=1, sticky=tk.W)

        # Porta
        ttk.Label(main_frame, text="Porta:").grid(row=2, column=0, sticky=tk.W)
        self.port_entry = ttk.Entry(main_frame, width=40)
        self.port_entry.insert(0, self.config['server_port'])
        self.port_entry.grid(row=2, column=1, sticky=tk.W)

        # Nome
        ttk.Label(main_frame, text="Nome do Servidor:").grid(row=3, column=0, sticky=tk.W)
        self.name_entry = ttk.Entry(main_frame, width=40)
        self.name_entry.insert(0, self.config['server_name'])
        self.name_entry.grid(row=3, column=1, sticky=tk.W)

        # RAM
        ttk.Label(main_frame, text="RAM Mínima:").grid(row=4, column=0, sticky=tk.W)
        self.min_ram_entry = ttk.Entry(main_frame, width=40)
        self.min_ram_entry.insert(0, self.config['min_ram'])
        self.min_ram_entry.grid(row=4, column=1, sticky=tk.W)

        ttk.Label(main_frame, text="RAM Máxima:").grid(row=5, column=0, sticky=tk.W)
        self.max_ram_entry = ttk.Entry(main_frame, width=40)
        self.max_ram_entry.insert(0, self.config['max_ram'])
        self.max_ram_entry.grid(row=5, column=1, sticky=tk.W)

        # Jar Path
        ttk.Label(main_frame, text="Arquivo do Servidor:").grid(row=6, column=0, sticky=tk.W)
        jar_frame = ttk.Frame(main_frame)
        jar_frame.grid(row=6, column=1, sticky=tk.W)
        
        self.jar_path_entry = ttk.Entry(jar_frame, width=30)
        self.jar_path_entry.insert(0, self.config['jar_path'])
        self.jar_path_entry.pack(side=tk.LEFT)
        
        ttk.Button(jar_frame, text="Procurar", command=self.select_jar).pack(side=tk.LEFT, padx=5)

        # Botões de controle
        control_frame = ttk.Frame(main_frame)
        control_frame.grid(row=7, column=0, columnspan=2, pady=10)
        
        self.start_button = ttk.Button(control_frame, text="Iniciar Servidor", command=self.start_server)
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        self.stop_button = ttk.Button(control_frame, text="Parar Servidor", command=self.stop_server, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(control_frame, text="Salvar Configurações", command=self.save_settings).pack(side=tk.LEFT, padx=5)

        # Log
        ttk.Label(main_frame, text="Log do Servidor", font=('', 12, 'bold')).grid(row=8, column=0, columnspan=2, pady=10)
        
        self.log_text = scrolledtext.ScrolledText(main_frame, height=15, width=70)
        self.log_text.grid(row=9, column=0, columnspan=2, sticky=(tk.W, tk.E))

        # Configurar grid
        self.window.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)

        # Iniciar atualização do log
        self.update_log()

        return self
    
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


class MainApplication(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Foxtail")
        
        self.width = 1200
        self.height = 720
        x = (self.winfo_screenwidth() - self.width) // 2
        y = (self.winfo_screenheight() - self.height) // 2
        self.geometry(f'{self.width}x{self.height}+{x}+{y}')
        
        self.db = TinyDB('db.json')
        self.setup_ui()
        self.plugins = {}
        self.rotinas = {}
        self.relatorios = {}
        # self.load_plugins()
        
    def setup_ui(self):
        configServer = ConfiguracoesServidor(self)
        configMine = ConfiguracoesMinecraft(self)

        # Menu
        self.menubar = tk.Menu(self)
        self.tools_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Ferramentas", menu=self.tools_menu)
        self.tools_menu.add_command(label="Configurações do servidor", command=configServer.activate)
        self.tools_menu.add_command(label="Configurações do minecraft", command=configMine.activate)
        self.config(menu=self.menubar)

        # Container principal
        self.main_container = tk.Frame(self)
        self.main_container.pack(expand=True, fill='both')

        # Background
        try:
            self.bg_image = Image.open("background.png")
            self.bg_image = self.bg_image.resize((self.width, self.height))  # Ajuste o tamanho do fundo para 1024x720
            self.bg_photo = ImageTk.PhotoImage(self.bg_image)
            self.bg_label = tk.Label(self.main_container, image=self.bg_photo)
            self.bg_label.place(x=0, y=0, relwidth=1, relheight=1)  # Use place() para ajustar ao fundo
        except Exception as e:
            print(f"Background error: {e}")

        # Widgets acima do background
        self.content_frame = tk.Frame(self.main_container)  # Adicione outros widgets no frame
        self.content_frame.pack(expand=False, fill='both')

        # Footer
        self.footer = tk.Frame(self)
        self.footer.pack(side='bottom', fill='x')
        self.db_status = tk.Label(self.footer, text="Status do servidor: OFFLINE")
        self.db_status.pack(side='left', padx=5)



    # ISSO AQUI ERA DE UM OUTRO PROGRAMA MEU, AINDA NÃO DECIDI SE VOU IMPLMENTAR
    # SUPORTE A PLUGIN NESSE 
                
    # def load_plugins(self):
    #     plugin_dir = "plugins"
    #     if not os.path.exists(plugin_dir):
    #         os.makedirs(plugin_dir)
    #         return
            
    #     for filename in os.listdir(plugin_dir):
    #         if filename.endswith(".py"):
    #             plugin_path = os.path.join(plugin_dir, filename)
    #             plugin_name = filename[:-3]
                
    #             try:
    #                 spec = importlib.util.spec_from_file_location(plugin_name, plugin_path)
    #                 module = importlib.util.module_from_spec(spec)
    #                 spec.loader.exec_module(module)
                    
    #                 if hasattr(module, 'Plugin'):
    #                     plugin = module.Plugin(self)
    #                     self.plugins[plugin_name] = plugin
                        
    #                     if plugin.type == "TOOL":
    #                         self.tools_menu.add_command(
    #                             label=plugin.name,
    #                             command=plugin.activate
    #                         )
    #                     elif plugin.type == "ROTINA":
    #                         if not hasattr(self, 'rotinas_menu'):
    #                             self.rotinas_menu = tk.Menu(self.menubar, tearoff=0)
    #                             self.menubar.add_cascade(label="Rotinas", menu=self.rotinas_menu)
    #                         self.rotinas_menu.add_command(
    #                             label=plugin.name,
    #                             command=plugin.activate
    #                         )

    #                     if plugin.on_startup:
    #                         plugin.on_startup()

    #             except Exception as e:
    #                 print(f"Error loading plugin {plugin_name}: {e}")

if __name__ == "__main__":
    app = MainApplication()
    app.mainloop()

