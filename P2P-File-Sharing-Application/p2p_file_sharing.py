import socket
import threading
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk


SERVER_HOST = "0.0.0.0"  # all network interfaces
BUFFER_SIZE = 1024       # Size of data 
SHARED_FOLDER = "shared" 
DOWNLOADS_FOLDER = "downloads" 


if not os.path.exists(SHARED_FOLDER):
    os.makedirs(SHARED_FOLDER)

if not os.path.exists(DOWNLOADS_FOLDER):
    os.makedirs(DOWNLOADS_FOLDER)

SERVER_IP = None
SERVER_PORT = None

# peers
def handle_peer_connection(client_socket, client_address):
    try:
        request = client_socket.recv(BUFFER_SIZE).decode('utf-8')

        if request.startswith("GET "):  
            filename = request.split()[1]
            file_path = os.path.join(SHARED_FOLDER, filename)

            if os.path.exists(file_path):
                client_socket.send(b"OK")
                with open(file_path, "rb") as file:
                    while chunk := file.read(BUFFER_SIZE):
                        client_socket.send(chunk)
            else:
                client_socket.send(b"FILE_NOT_FOUND")
        else:
            client_socket.send(b"INVALID_REQUEST")
    finally:
        client_socket.close()

# Server (listening to connections)
def start_server(gui_update_network_details):
    global SERVER_IP, SERVER_PORT
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((SERVER_HOST, 0))  
    SERVER_IP = socket.gethostbyname(socket.gethostname())  
    SERVER_PORT = server_socket.getsockname()[1]  
    gui_update_network_details(SERVER_IP, SERVER_PORT)  
    server_socket.listen(10)

    while True:
        client_socket, client_address = server_socket.accept()
        threading.Thread(target=handle_peer_connection, args=(client_socket, client_address)).start()

#Request from peer
def request_file(peer_host, peer_port, filename, gui_log):
    try:
        peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        peer_socket.connect((peer_host, peer_port))
        peer_socket.send(f"GET {filename}".encode('utf-8'))

        response = peer_socket.recv(BUFFER_SIZE).decode('utf-8')
        if response == "OK":
            download_path = os.path.join(DOWNLOADS_FOLDER, filename)
            with open(download_path, "wb") as file:
                while chunk := peer_socket.recv(BUFFER_SIZE):
                    file.write(chunk)
            gui_log(f"File '{filename}' downloaded successfully to {download_path}.")
        elif response == "FILE_NOT_FOUND":
            gui_log(f"File '{filename}' not found on peer.")
        else:
            gui_log(f"Invalid response from peer.")
    except Exception as e:
        gui_log(f"Error: {e}")
    finally:
        peer_socket.close()


class P2PApp:
    def __init__(self, root):
        self.root = root
        self.root.title("P2P File Sharing")
        self.root.geometry("700x400")

        
        self.top_frame = ttk.Frame(self.root)
        self.top_frame.pack(pady=10)

        self.middle_frame = ttk.Frame(self.root)
        self.middle_frame.pack(pady=10, fill="both", expand=True)

        self.bottom_frame = ttk.Frame(self.root)
        self.bottom_frame.pack(pady=10)

        
        self.peer_ip_label = ttk.Label(self.top_frame, text="Peer IP:")
        self.peer_ip_label.grid(row=0, column=0, padx=5)

        self.peer_ip_entry = ttk.Entry(self.top_frame, width=20)
        self.peer_ip_entry.grid(row=0, column=1, padx=5)

        self.peer_port_label = ttk.Label(self.top_frame, text="Peer Port:")
        self.peer_port_label.grid(row=0, column=2, padx=5)

        self.peer_port_entry = ttk.Entry(self.top_frame, width=10)
        self.peer_port_entry.grid(row=0, column=3, padx=5)

        self.filename_label = ttk.Label(self.top_frame, text="Filename:")
        self.filename_label.grid(row=0, column=4, padx=5)

        self.filename_entry = ttk.Entry(self.top_frame, width=20)
        self.filename_entry.grid(row=0, column=5, padx=5)

        self.request_button = ttk.Button(self.top_frame, text="Request File", command=self.request_file)
        self.request_button.grid(row=0, column=6, padx=5)

        self.shared_files_label = ttk.Label(self.middle_frame, text="Shared Files:")
        self.shared_files_label.pack(anchor="w")

        self.shared_files_listbox = tk.Listbox(self.middle_frame, height=10)
        self.shared_files_listbox.pack(fill="both", expand=True)

        self.add_file_button = ttk.Button(self.bottom_frame, text="Add File", command=self.add_file)
        self.add_file_button.pack(side="left", padx=10)

        self.refresh_button = ttk.Button(self.bottom_frame, text="Refresh", command=self.refresh_shared_files)
        self.refresh_button.pack(side="left", padx=10)

        self.exit_button = ttk.Button(self.bottom_frame, text="Exit", command=self.root.quit)
        self.exit_button.pack(side="left", padx=10)

        self.network_details_label = ttk.Label(self.bottom_frame, text="Your Details: IP - N/A | Port - N/A")
        self.network_details_label.pack(side="right", padx=10)

        
        threading.Thread(target=start_server, args=(self.update_network_details,), daemon=True).start()

        
        self.refresh_shared_files()

    def update_network_details(self, ip, port):
        self.network_details_label.config(text=f"Your Details: IP - {ip} | Port - {port}")

    def log_message(self, message):
        messagebox.showinfo("P2P File Sharing", message)

    def refresh_shared_files(self):
        self.shared_files_listbox.delete(0, tk.END)
        for file in os.listdir(SHARED_FOLDER):
            self.shared_files_listbox.insert(tk.END, file)

    def add_file(self):
        file_path = filedialog.askopenfilename()
        if file_path:
            file_name = os.path.basename(file_path)
            dest_path = os.path.join(SHARED_FOLDER, file_name)
            if not os.path.exists(dest_path):
                os.rename(file_path, dest_path)
                self.refresh_shared_files()
                self.log_message(f"File '{file_name}' added to shared folder.")

    def request_file(self):
        peer_ip = self.peer_ip_entry.get().strip()
        peer_port = self.peer_port_entry.get().strip()
        filename = self.filename_entry.get().strip()

        if not peer_ip or not peer_port or not filename:
            self.log_message("Please fill in all fields.")
            return

        threading.Thread(target=request_file, args=(peer_ip, int(peer_port), filename, self.log_message)).start()


if __name__ == "__main__":
    root = tk.Tk()
    app = P2PApp(root)
    root.mainloop()
