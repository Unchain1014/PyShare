import os
import sys
import tkinter as tk
from tkinter import messagebox
import socket
import threading

class PyKitApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PyShare")
        self.root.geometry("500x250")
        self.root.resizable(False, False)

        # Set the application icon
        if getattr(sys, 'frozen', False):  # Check if running as a PyInstaller bundle
            base_path = sys._MEIPASS  # Path to the temporary folder created by PyInstaller
        else:
            base_path = os.path.dirname(__file__)  # Path to the script directory

        icon_path = os.path.join(base_path, "icon.ico")  # Adjust path to the images folder
        try:
            self.root.iconbitmap(icon_path)  # Set the icon for the main window
        except Exception as e:
            print(f"Error setting icon: {e}")

        # Center the window on the screen
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        x = (screen_width // 2) - (500 // 2)
        y = (screen_height // 2) - (250 // 2)
        self.root.geometry(f"500x250+{x}+{y}")

        # Get the user's IP address
        user_ip = self.get_ip_address()

        # Create a frame to hold the labels and buttons
        label_frame = tk.Frame(root)
        label_frame.pack(expand=True, pady=20)

        # Add an Entry widget to display the user's IP address (copyable)
        ip_entry = tk.Entry(
            label_frame,
            font=("Arial", 12, "bold"),
            fg="#333333",
            justify="center",
            width=20
        )
        ip_entry.insert(0, user_ip)  # Insert the IP address into the Entry widget
        ip_entry.config(state="readonly")  # Make the Entry widget read-only
        ip_entry.grid(row=1, column=0, pady=(0, 0), padx=(0, 10))

        # Add a button to copy the IP address to the clipboard
        copy_button = tk.Button(
            label_frame,
            text="Copy",
            font=("Arial", 10),
            width=10,  # Set a fixed width for the button
            command=lambda: self.copy_to_clipboard(user_ip)
        )
        copy_button.grid(row=1, column=1)

        # Add an empty Entry widget for pasting an IP address
        join_entry = tk.Entry(
            label_frame,
            font=("Arial", 12, "bold"),
            fg="#333333",
            justify="center",
            width=20
        )
        join_entry.grid(row=2, column=0, padx=(0, 10), pady=(10, 0))

        # Add a button to join the entered IP address
        join_button = tk.Button(
            label_frame,
            text="Join",
            font=("Arial", 10),
            width=10,  # Set the same fixed width for the button
            command=lambda: self.join_ip(join_entry.get())  # Attempt to connect to the entered IP
        )
        join_button.grid(row=2, column=1, pady=(10, 0))

        # Add a status label at the bottom
        self.status_label = tk.Label(
            root,
            text="Status: OFFLINE",
            font=("Arial", 10, "bold"),
            fg="white",
            bg="#8B0000"  # Deep red for offline
        )
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X)

        # Start checking the connection status
        self.connected_to_client = False
        self.check_connection_status()

        # Default port for communication
        self.default_port = 5000

        # Start a server thread to listen for incoming connections
        self.server_thread = threading.Thread(target=self.start_server, daemon=True)
        self.server_thread.start()

        # Other UI setup...
        self.connected_to_client = False
        self.check_connection_status()

    def get_ip_address(self):
        """Retrieve the user's local IP address."""
        try:
            # Create a dummy socket to get the local IP address
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))  # Connect to a public DNS server
            ip_address = s.getsockname()[0]
            s.close()
            return ip_address
        except Exception as e:
            print(f"Error retrieving IP address: {e}")
            return "IP Not Found"

    def copy_to_clipboard(self, text):
        """Copy the given text to the clipboard."""
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.root.update()  # Update the clipboard
        messagebox.showinfo("Copied", "IP address copied to clipboard!")

    def start_server(self):
        """Start a server to listen for incoming connections."""
        try:
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.bind(("", self.default_port))
            server_socket.listen(1)
            print(f"Server listening on port {self.default_port}...")

            while True:
                client_socket, client_address = server_socket.accept()
                print(f"Connected to {client_address}")
                self.connected_to_client = True
                self.status_label.config(text="Status: CONNECTED", fg="white", bg="#32CD32")  # Soft green

                # Keep the connection open for communication
                threading.Thread(target=self.handle_client, args=(client_socket,)).start()
        except Exception as e:
            print(f"Error starting server: {e}")

    def join_ip(self, ip_address):
        """Attempt to connect to the entered IP address."""
        if not ip_address.strip():  # Check if the IP address is blank
            messagebox.showwarning("Invalid Input", "Please enter an IP address to connect.")
            return

        try:
            self.client_socket = socket.create_connection((ip_address, self.default_port), timeout=5)
            print(f"Connected to {ip_address}:{self.default_port}")
            self.connected_to_client = True
            self.status_label.config(text="Status: CONNECTED", fg="white", bg="#32CD32")  # Soft green

            # Keep the connection open for communication
            threading.Thread(target=self.handle_server, args=(self.client_socket,)).start()
        except Exception as e:
            print(f"Failed to connect to {ip_address}: {e}")
            messagebox.showerror("Connection Failed", f"Could not connect to {ip_address}.\nError: {e}")
            self.connected_to_client = False

    def handle_client(self, client_socket):
        """Handle communication with a connected client."""
        try:
            while True:
                # Example: Receive data from the client
                data = client_socket.recv(1024)
                if not data:
                    break
                print(f"Received: {data.decode()}")
        except Exception as e:
            print(f"Error handling client: {e}")
        finally:
            client_socket.close()
            self.connected_to_client = False
            print("Client disconnected")

    def handle_server(self, server_socket):
        """Handle communication with the server."""
        try:
            while True:
                # Example: Receive data from the server
                data = server_socket.recv(1024)
                if not data:
                    break
                print(f"Received from server: {data.decode()}")
        except Exception as e:
            print(f"Error handling server: {e}")
        finally:
            server_socket.close()
            self.connected_to_client = False
            print("Disconnected from server")

    def check_connection_status(self):
        """Check the internet connection and update the status label."""
        if self.connected_to_client:
            self.status_label.config(text="Status: CONNECTED", fg="white", bg="#32CD32")  # Soft green
        else:
            if self.is_connected_to_internet():
                self.status_label.config(text="Status: ONLINE", fg="black", bg="#DDDDDD")  # Light gray
            else:
                self.status_label.config(text="Status: OFFLINE", fg="white", bg="#8B0000")  # Deep red
        self.root.after(1000, self.check_connection_status)

    def is_connected_to_internet(self):
        """Check if the machine is connected to the internet."""
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=2)
            return True
        except OSError:
            return False

    def setup_p2p(self):
        """Placeholder for P2P setup logic."""
        # This is where the P2P file transfer logic will be implemented
        pass

if __name__ == "__main__":
    root = tk.Tk()

    # Set the application icon
    if getattr(sys, 'frozen', False):  # Check if running as a PyInstaller bundle
        base_path = sys._MEIPASS  # Path to the temporary folder created by PyInstaller
    else:
        base_path = os.path.dirname(__file__)  # Path to the script directory

    icon_path = os.path.join(base_path, "icon.ico")  # Adjust path to the images folder
    try:
        root.iconbitmap(icon_path)  # Set the icon for the main window
    except Exception as e:
        print(f"Error setting icon: {e}")

    app = PyKitApp(root)
    root.mainloop()