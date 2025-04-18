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

        self.icon_path = icon_path  # Add this in __init__

        # Center the window on the screen
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        x = (screen_width // 2) - (500 // 2)
        y = (screen_height // 2) - (250 // 2)
        self.root.geometry(f"500x250+{x}+{y}")

        # Add a status label at the bottom
        self.status_label = tk.Label(
            root,
            text="Status: OFFLINE",
            font=("Arial", 10, "bold"),
            fg="white",
            bg="#8B0000"  # Deep red for offline
        )
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X)

        # Get the user's IP address
        user_ip = self.get_ip_address()

        # Create a frame to hold the labels and buttons
        label_frame = tk.Frame(root)
        label_frame.pack(expand=True, pady=20)

        # Start checking the connection status
        self.connected_to_client = False
        self.check_connection_status()

        # Default port for communication
        self.default_port = 5000

        # Start a server thread to listen for incoming connections
        self.server_thread = threading.Thread(target=self.start_server, daemon=True)
        self.server_thread.start()

        # Add an Entry widget to display the user's IP address (copyable)
        ip_entry = tk.Entry(
            label_frame,
            font=("Arial", 12),
            fg="#333333",
            justify="center",
            width=30  # Adjust width to accommodate IP and port
        )
        ip_with_port = f"{user_ip}:{self.default_port}"  # Combine IP and port
        ip_entry.insert(0, ip_with_port)  # Insert the IP address and port into the Entry widget
        ip_entry.config(state="readonly")  # Make the Entry widget read-only
        ip_entry.grid(row=1, column=0, pady=(0, 0), padx=(0, 10))

        # Add a button to copy the IP address to the clipboard
        copy_button = tk.Button(
            label_frame,
            text="Copy",
            font=("Arial", 10),
            width=10,  # Set a fixed width for the button
            command=lambda: self.copy_to_clipboard(ip_with_port)  # Copy IP and port
        )
        copy_button.grid(row=1, column=1)

        # Add an empty Entry widget for pasting an IP address
        join_entry = tk.Entry(
            label_frame,
            font=("Arial", 12),
            fg="#333333",
            justify="center",
            width=30
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
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                server_socket.bind(("", self.default_port))
                print(f"Server listening on UDP port {self.default_port}...")
            except OSError as e:
                print(f"Error binding to port {self.default_port}: {e}")
                messagebox.showerror("Server Error", f"Could not bind to port {self.default_port}. Is it already in use?")
                return

            while True:
                try:
                    data, addr = server_socket.recvfrom(1024)
                    print(f"Received message from {addr}: {data.decode()}")
                    if data.decode() == "Hello":
                        # Respond to the peer to complete the hole punching
                        server_socket.sendto(b"Hello back!", addr)
                        print(f"Responded to {addr}")
                        self.connected_to_client = True
                        self.status_label.config(text="Status: CONNECTED", fg="white", bg="#32CD32")  # Soft green
                except Exception as e:
                    print(f"Error receiving data: {e}")
        except Exception as e:
            print(f"Error starting server: {e}")

    def udp_hole_punching(self, local_port, peer_ip, peer_port):
        """Establish a direct connection using UDP hole punching and enable data exchange."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.bind(("", local_port))
                print(f"Listening on UDP port {local_port}...")

                # Send a packet to the peer to create a NAT mapping
                s.sendto(b"Hello", (peer_ip, peer_port))
                print(f"Sent hole-punching packet to {peer_ip}:{peer_port}")

                # Wait for a response from the peer
                s.settimeout(5)  # Timeout after 5 seconds
                data, addr = s.recvfrom(1024)
                if data.decode() == "Hello back!":
                    print(f"Connection established with {addr}")
                    self.connected_to_client = True
                    self.status_label.config(text="Status: CONNECTED", fg="white", bg="#32CD32")  # Soft green

                    # Start the keep-alive thread
                    threading.Thread(target=self.keep_alive, args=(peer_ip, peer_port), daemon=True).start()

                    # Start a thread to handle data exchange
                    threading.Thread(target=self.handle_udp_chat, args=(s, addr), daemon=True).start()
                else:
                    raise Exception("Unexpected response")
        except socket.timeout:
            print("Connection timed out")
            messagebox.showerror("Connection Failed", "Connection timed out. NAT traversal failed.")
        except Exception as e:
            print(f"Error during hole punching: {e}")
            messagebox.showerror("Connection Failed", f"Error during connection: {e}")

    def join_ip(self, ip_address):
        """Attempt to connect to the entered IP address."""
        if not ip_address.strip():  # Check if the IP address is blank
            messagebox.showwarning("Invalid Input", "Please enter an IP address to connect.")
            return

        try:
            peer_ip, peer_port = ip_address.split(":")
            peer_port = int(peer_port)
            threading.Thread(target=self.udp_hole_punching, args=(self.default_port, peer_ip, peer_port)).start()
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter a valid IP address and port (e.g., 192.168.1.100:5000).")
        except Exception as e:
            print(f"Failed to initiate connection: {e}")

    def keep_alive(self, peer_ip, peer_port):
        """Send periodic keep-alive packets to the peer."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                while self.connected_to_client:
                    s.sendto(b"PING", (peer_ip, peer_port))
                    print(f"Sent keep-alive packet to {peer_ip}:{peer_port}")
                    threading.Event().wait(5)  # Wait 5 seconds before sending the next packet
        except Exception as e:
            print(f"Error in keep-alive: {e}")

    def check_connection_status(self):
        """Check the internet connection and update the status label."""
        if self.connected_to_client:
            self.status_label.config(text="Status: CONNECTED", fg="white", bg="#32CD32")  # Soft green
        else:
            if self.is_connected_to_internet():
                self.status_label.config(text="Status: ONLINE", fg="black", bg="#DDDDDD")  # Light gray
            else:
                self.status_label.config(text="Status: OFFLINE", fg="white", bg="#8B0000")  # Deep red

        # Schedule the next check
        self.connection_status_timer = self.root.after(1000, self.check_connection_status)

    def is_connected_to_internet(self):
        """Check if the machine is connected to the internet."""
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=2)
            return True
        except OSError:
            return False
        
    def handle_udp_chat(self, udp_socket, peer_addr):
        """Handle chat messages over the established UDP connection."""
        def send_message(event=None):  # Add `event` parameter to handle key binding
            """Send a message to the peer."""
            message = chat_entry.get()
            if message.strip():  # Only send non-empty messages
                udp_socket.sendto(message.encode(), peer_addr)
                # Temporarily enable the chat box to insert the message
                chat_box.config(state="normal")
                chat_box.insert(tk.END, f"You: {message}\n")
                chat_box.config(state="disabled")  # Set back to read-only
                chat_box.see(tk.END)  # Scroll to the latest message
                chat_entry.delete(0, tk.END)

        def receive_messages():
            """Receive messages from the peer."""
            try:
                while self.connected_to_client:
                    data, addr = udp_socket.recvfrom(1024)
                    if data:
                        # Temporarily enable the chat box to insert the message
                        chat_box.config(state="normal")
                        chat_box.insert(tk.END, f"Peer: {data.decode()}\n")
                        chat_box.config(state="disabled")  # Set back to read-only
                        chat_box.see(tk.END)  # Scroll to the latest message
            except Exception as e:
                print(f"Error during chat: {e}")
            finally:
                self.connected_to_client = False
                print("Disconnected from peer")

        # Create the chat window
        chat_window = tk.Toplevel(self.root)
        chat_window.title("Chat")
        chat_window.geometry("400x300")
        chat_window.iconbitmap(self.icon_path)  # Set the icon for the chat window

        # Chat box (scrollable)
        chat_box = tk.Text(chat_window, state="disabled", wrap="word", height=15, width=50)
        chat_box.pack(pady=10, padx=10)

        # Chat entry field
        chat_entry = tk.Entry(chat_window, font=("Arial", 12))
        chat_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 0), pady=(0, 10))

        # Bind the Enter key to the send_message function
        chat_entry.bind("<Return>", send_message)

        # Send button
        send_button = tk.Button(chat_window, text="Send", font=("Arial", 10), command=send_message)
        send_button.pack(side=tk.RIGHT, padx=(0, 10), pady=(0, 10))

        # Start a thread to receive messages
        threading.Thread(target=receive_messages, daemon=True).start()

    def send_file_udp(self, file_path, peer_ip, peer_port):
        """Send a file to the peer over UDP."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                with open(file_path, "rb") as f:
                    while chunk := f.read(1024):  # Read the file in chunks of 1024 bytes
                        s.sendto(chunk, (peer_ip, peer_port))
                        print(f"Sent chunk to {peer_ip}:{peer_port}")
                # Send an empty packet to indicate the end of the file
                s.sendto(b"", (peer_ip, peer_port))
                print("File transfer complete.")
        except Exception as e:
            print(f"Error sending file: {e}")

    def receive_file_udp(self, save_path, local_port):
        """Receive a file from the peer over UDP."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.bind(("", local_port))
                print(f"Listening for file on UDP port {local_port}...")
                with open(save_path, "wb") as f:
                    while True:
                        data, addr = s.recvfrom(1024)
                        if not data:  # Empty packet indicates the end of the file
                            break
                        f.write(data)
                        print(f"Received chunk from {addr}")
                print("File received successfully.")
        except Exception as e:
            print(f"Error receiving file: {e}")

    def cleanup(self):
        """Cleanup resources when the program exits."""
        if hasattr(self, 'connection_status_timer'):
            self.root.after_cancel(self.connection_status_timer)
        print("Cleaned up resources.")

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

    # Bind cleanup to the window close event
    root.protocol("WM_DELETE_WINDOW", lambda: (app.cleanup(), root.destroy()))

    root.mainloop()