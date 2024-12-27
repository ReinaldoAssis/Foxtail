import threading
import tkinter as tk
from tinydb import TinyDB, Query
from PIL import Image, ImageTk

from Autoupdate import AutoUpdater
from ConfiguracoesServidor import ConfiguracoesServidor
from ConfiguracoesMinecraft import ConfiguracoesMinecraft

# !!!! IGNORAR: Estou mantendo tudo em um arquivo só porque ainda não sei como vai ser para fazer o executavel, então
# para evitar problemas preferi manter tudo em um lugar só. !!!!

# !!!! @UPDATE: Não é necessário manter tudo em um arquivo, estou dividindo agora com cada interface tendo seu arquivo.
# gostaria de separar em pastas, mas isso complica a importação, por hora deixarei assim mesmo.

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
        self.version = "dev241227"
        query = Query()
        self.db.upsert({"version": self.version}, query.version == self.version)
        # self.load_plugins()

        self.updater = AutoUpdater(self.version, self)
        threading.Thread(target=self.updater.check_for_updates, daemon=True).start()
        
    # implement function to read https://github.com/ReinaldoAssis/Foxtail/blob/main/db.json and
    # get the "version" value, compare with the current version and if it is different
    # make a pop up appear with a message asking if the user wants to update, if the user
    # agrees a progress bar should appear and a thread will download to the current directory the latest release
    # from the github (.exe if on windows and different if on mac)
    # when completed a process should be schedule to close the current version, delete it and open the new one

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

