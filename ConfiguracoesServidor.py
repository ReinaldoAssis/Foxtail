import os
import platform
import queue
import signal
import subprocess
import socket  # Add this import
from threading import Thread
import tkinter as tk
from tkinter import Tk, filedialog
from tkinter import ttk
from tkinter import scrolledtext


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
            'max_ram': '4G',
            'host_ip': '',
            'tunnel_address': ''
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
                self.log_text.see(tk.END)  # Change Tk.END to tk.END
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
        self.config['host_ip'] = self.host_ip_entry.get()
        self.config['tunnel_address'] = self.tunnel_address_entry.get()
        self.save_config()
        self.log_queue.put("Configurações salvas com sucesso!\n")

    def auto_fill_ip(self):
        hostname = socket.gethostname()
        ip_address = socket.gethostbyname(hostname)
        self.host_ip_entry.delete(0, tk.END)
        self.host_ip_entry.insert(0, ip_address)
        self.log_queue.put("IP da máquina preenchido automaticamente.\n")

    def configure_tunnel(self):
        self.log_queue.put("Configuração do túnel chamada.\n")
        # Placeholder for tunnel configuration logic

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

        notebook = ttk.Notebook(self.window)
        notebook.pack(expand=True, fill='both', padx=10, pady=5)

        # Tab Configurações do Servidor
        server_frame = ttk.Frame(notebook, padding=10)
        notebook.add(server_frame, text='Servidor Minecraft')

        # Frame principal
        main_frame = ttk.Frame(server_frame, padding="10")
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

        # Tab Configurações do Host
        host_frame = ttk.Frame(notebook, padding=10)
        notebook.add(host_frame, text='Configurações do Host')

        ttk.Label(host_frame, text="Configurações do Host", font=('', 12, 'bold')).grid(row=0, column=0, columnspan=2, pady=10)

        # IP da Máquina
        ttk.Label(host_frame, text="IP da Máquina:").grid(row=1, column=0, sticky=tk.W)
        self.host_ip_entry = ttk.Entry(host_frame, width=40)
        self.host_ip_entry.insert(0, self.config.get('host_ip', ''))
        self.host_ip_entry.grid(row=1, column=1, sticky=tk.W)

        ttk.Button(host_frame, text="Preencher IP", command=self.auto_fill_ip).grid(row=1, column=2, padx=5)

        # Endereço do Túnel
        ttk.Label(host_frame, text="Endereço do Túnel:").grid(row=2, column=0, sticky=tk.W)
        self.tunnel_address_entry = ttk.Entry(host_frame, width=40)
        self.tunnel_address_entry.insert(0, self.config.get('tunnel_address', ''))
        self.tunnel_address_entry.grid(row=2, column=1, sticky=tk.W)

        ttk.Button(host_frame, text="Configurar Túnel", command=self.configure_tunnel).grid(row=2, column=2, padx=5)

        # Log
        ttk.Label(host_frame, text="Log do Host", font=('', 12, 'bold')).grid(row=3, column=0, columnspan=2, pady=10)
        
        self.host_log_text = scrolledtext.ScrolledText(host_frame, height=15, width=70)
        self.host_log_text.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E))

        # Botões de controle
        control_frame = ttk.Frame(host_frame)
        control_frame.grid(row=5, column=0, columnspan=3, pady=10)
        
        ttk.Button(control_frame, text="Salvar Configurações", command=self.save_settings).pack(side=tk.LEFT, padx=5)

        # Iniciar atualização do log
        self.update_log()

        return self