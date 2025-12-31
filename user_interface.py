from kivy.app import App
from kivy.uix.gridlayout import GridLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from FaceReaderConnector import FaceReaderConnector
import json 
import threading
from kivy.uix.widget import Widget
from kivy.uix.spinner import Spinner

class FaceReaderApp(App):
    
    def __init__(self, FaceReaderCon: FaceReaderConnector, **kwargs):
        super().__init__(**kwargs)
        self.FaceReaderCon = FaceReaderCon
        self.global_session = None
    
    
    ### CONNECTION SUITE
    def connect_to_face_reader(self, instance):
        try:
            self.FaceReaderCon.connect()
            self.log_input.text = "Face Reader Connected Succesfully"
            # self.FaceReaderCon.send_action_message("FaceReader_Start_Analyzing")
        except Exception as e:
            self.log_input.text = f"Error in connection, have you started the Face Reader Software? \n Error: {e}"        

    def disconnect_from_face_reader(self, instance):
        self.FaceReaderCon.send_action_message("FaceReader_Stop_Analyzing")
        self.FaceReaderCon.disconnect()

    def send_to_server(self, instance):
        # Implement the logic to send data to the server
        self.global_session = threading.Thread(target=self.FaceReaderCon.start_session)
        self.global_session.start()
        self.log_input.text = f"Start Sending LLAMA Server"        

    def stop_send_to_server(self, instance):
        # Implement the logic to stop sending data to the server
        if self.FaceReaderCon.sock:
            self.FaceReaderCon.stop_session()
            self.global_session.join()
            self.log_input.text = f"Stop Sending LLAMA Server"        

    def aggregate_emotions(self, instance):
        response = self.FaceReaderCon.aggregate_emotions()
        self.log_input.text = response
        
    def set_log_dir(self, instance):
        self.FaceReaderCon.set_log_dir(f"{self.log_name.text}")
        self.log_input.text = f"Name and surname set to: {self.log_name.text}"
    
    def set_stimuli(self, instance):
        response = self.FaceReaderCon.set_stimuli(f"{self.stimulus_spinner.text}")
        self.log_input.text = response
    
    def restart_server(self, instance):
        response = self.FaceReaderCon.restart_server()
        self.log_input.text = f"{response}"
        
    
    def build(self):
        main_layout = BoxLayout(orientation = "vertical", spacing=2)
        title = Label(
            text="Face Reader Control Panel",
            font_size=20,
            size_hint_y=None,
            height=100,
            halign="center",
            valign="middle"
        )
        title.bind(size=title.setter("text_size"))
        # main_layout.add_widget(Label(text='Face Reader Control Panel', font_size=15, halign='center'))
        btn_restart = Button(
            text="Restart server",
            on_press=self.restart_server,
            size_hint_y=None,
            height=100,
            padding=(5, 2)
        )        
        # grid_layout1 = GridLayout(cols=1, spacing=10, padding=10)
        # main_layout.add_widget(btn_restart)
        
        main_layout.add_widget(title)
        # main_layout.add_widget(btn_restart)
                       
        # Row 2: Connect and Disconnect buttons
        grid_layout = GridLayout(cols=3, spacing=5, padding=5)

        # label_name = Label(text='Insert here name and surname', font_size=20, halign='center')
        self.log_name = TextInput(hint_text='Insert here name and surname', multiline=True)
        
        btn_save_name_surname = Button(text='Set user name', on_press = self.set_log_dir)
        
        # grid_layout.add_widget(label_name,)
        grid_layout.add_widget(self.log_name)
        grid_layout.add_widget(btn_save_name_surname)
        
        grid_layout.add_widget(Widget())
        
        self.stimulus_spinner = Spinner(
            text="Select stimulus",
            values=("mufasa", "benigni"),
            size_hint=(1, None),
            # height=40
        )
        
        grid_layout.add_widget(self.stimulus_spinner)
        grid_layout.add_widget(Button(text='Set Stimuli', on_press = self.set_stimuli))

        grid_layout.add_widget(Widget())
        

        grid_layout.add_widget(Button(text='Connect to Face Reader', on_press = self.connect_to_face_reader))
        grid_layout.add_widget(Button(text='Disconnect from Face Reader', on_press = self.disconnect_from_face_reader))
        grid_layout.add_widget(Widget())

        # Row 3: Send and Stop buttons
        grid_layout.add_widget(Button(text='Send to Server (video)', on_press = self.send_to_server))
        grid_layout.add_widget(Button(text='Stop Sending to Server(video)', on_press = self.stop_send_to_server))
        grid_layout.add_widget(Button(text='Aggregate Emotions (video)', on_press = self.aggregate_emotions))

        # INTERRUPT
        main_layout.add_widget(grid_layout)
        main_layout.add_widget(btn_restart)
        
        # novel grid
        grid_layout2 = GridLayout(cols=3, spacing=5, padding=5)

        # Row 4: Send and Stop buttons
        grid_layout2.add_widget(Button(text='Connect to Face Reader', on_press = self.connect_to_face_reader))
        grid_layout2.add_widget(Button(text='Disconnect from Face Reader', on_press = self.disconnect_from_face_reader))
        grid_layout2.add_widget(Widget())

        grid_layout2.add_widget(Button(text='Send to Server (CHAT)', on_press = self.send_to_server))
        grid_layout2.add_widget(Button(text='Stop Sending to Server(CHAT)', on_press = self.stop_send_to_server))
        grid_layout2.add_widget(Widget())
      
        # grid_layout2.add_widget(Button(text='Send to Server (video)', on_press = self.send_to_server))
        # grid_layout2.add_widget(Button(text='Stop Sending to Server(video)', on_press = self.stop_send_to_server))
        # grid_layout2.add_widget(Widget())

        main_layout.add_widget(grid_layout2)

        # Row 4: Log field spanning two columns using BoxLayout
        h_box_layout = BoxLayout(orientation='horizontal', spacing=10, size_hint_y=None, height=100)
        self.log_input = TextInput(hint_text='Logs will appear here...', multiline=True)
        h_box_layout.add_widget(self.log_input)
        
       

        main_layout.add_widget(h_box_layout)

        return main_layout


if __name__ == '__main__':
    config_data = json.load(open("config.json"))    
    connector = FaceReaderConnector(
        host=config_data["HOST"],
        port=config_data["PORT"],
        server_url = config_data["SERVER_URL"],
        log_dir='logs'
    )
    FaceReaderApp(FaceReaderCon=connector).run()