from kivy.app import App
from kivy.uix.gridlayout import GridLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from FaceReaderConnector import FaceReaderConnector
import json 

class FaceReaderApp(App):
    
    def __init__(self, FaceReaderCon: FaceReaderConnector, **kwargs):
        super().__init__(**kwargs)
        self.FaceReaderCon = FaceReaderCon
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
        pass
    
    def set_log_dir(self, instance):
        self.FaceReaderCon.set_log_dir(f"{self.log_name.text}")
        self.log_input.text = f"Name and surname set to: {self.log_name.text}"
    
    def stop_send_to_server(self, instance):
        # Implement the logic to stop sending data to the server
        pass
    
    def build(self):
        main_layout = BoxLayout(orientation='vertical', spacing=1)
        main_layout.add_widget(Label(text='Face Reader Control Panel', font_size=20, halign='center'))

        grid_layout = GridLayout(cols=2, spacing=10, padding=10)

        # Row 2: Connect and Disconnect buttons
        # label_name = Label(text='Insert here name and surname', font_size=20, halign='center')
        self.log_name = TextInput(hint_text='Insert here name and surname', multiline=True)
        
        btn_save_name_surname = Button(text='Set user name', on_press = self.set_log_dir)
        
        # grid_layout.add_widget(label_name,)
        grid_layout.add_widget(self.log_name)
        grid_layout.add_widget(btn_save_name_surname)


        grid_layout.add_widget(Button(text='Connect to Face Reader', on_press = self.connect_to_face_reader))
        grid_layout.add_widget(Button(text='Disconnect from Face Reader', on_press = self.disconnect_from_face_reader))

        # Row 3: Send and Stop buttons
        grid_layout.add_widget(Button(text='Send to Server'))
        grid_layout.add_widget(Button(text='Stop Sending to Server'))

        
        # Row 4: Log field spanning two columns using BoxLayout
        h_box_layout = BoxLayout(orientation='horizontal', spacing=10, size_hint_y=None, height=50)
        self.log_input = TextInput(hint_text='Logs will appear here...', multiline=True)
        h_box_layout.add_widget(self.log_input)
        
        main_layout.add_widget(grid_layout)
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
