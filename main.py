# Asynchronous Chat Server

from flask import Flask, render_template, redirect, request, url_for, flash, session
from flask_socketio import SocketIO, emit, join_room, leave_room
import uuid
import os
from datetime import datetime
from g_room_code import generate_room_key
import secrets

app = Flask(__name__)
app.secret_key = secrets.token_urlsafe(32)

# Add SocketIO support
socketio = SocketIO(app, cors_allowed_origins="*")

# Store active users in rooms
room_users = {}  # {room_code: {username: session_id}}

@app.route("/")
def home_page():
    return render_template('index.html')

app.config["UPLOAD_FOLDER"] = "assets"

@app.route("/login", methods=["GET", "POST"])
def login_page():
    myid = uuid.uuid1()
    print(request.method)
    if request.method == "POST":
        d_t = datetime.now()
        date_str = d_t.strftime("%Y-%m-%d")
        time_str = d_t.strftime("%I:%M:%S %p") 
        user_id = request.form.get("uuid")  
        name = request.form.get("name")
        session['username_fetched'] = request.form.get("name", "Guest")
        email = request.form.get("email")
        data = f"Name: {name} \nEmail: {email} \nKEY: {user_id} \nDATE: {date_str} \nTIME: {time_str}"
        data_folder = os.path.join("assets", user_id)
        if not os.path.exists(data_folder):
            os.makedirs(data_folder, exist_ok=True)
        with open(os.path.join(data_folder, "details.txt"), "w") as f:
            f.write(data)
        return redirect(url_for("chat_page", room_code="None"))

    return render_template("login_details.html", myid=myid)

@app.route("/chatpage/<room_code>")
def chat_page(room_code):
    try:
        with open('g_code.txt') as f:
            valid_key = f.read().strip()  
    except FileNotFoundError:
        valid_key = ""
    
    if room_code == valid_key:
        show_overlay = False
    else:
        show_overlay = True
    
    username = session.get("username_fetched")
    return render_template('chatpage.html', 
                         username=username, 
                         show_overlay=show_overlay,
                         room_code=room_code)

@app.route("/join", methods=["GET", "POST"])
def join_page():
    if request.method == "POST":  
        vcode = request.form.get("room_code")
        with open("p_code.txt", "w") as dd:
            dd.write(vcode)
        try:
            with open("g_code.txt") as fff:
                x1 = fff.read().strip() 
        except FileNotFoundError:
            x1 = ""
            
        if x1 == vcode:
            return redirect(url_for("chat_page", room_code=vcode))
        else:
            flash("OOPS WRONG CODE!!")
            return redirect(url_for("join_page"))
    return render_template('join.html')

@app.route("/create", methods=["GET"])
def create_page():
    code = generate_room_key()
    username = session.get('username_fetched') 
    
    with open("g_code.txt", "w") as ff:
        ff.write(code)
    return render_template('createchat.html', code=code)

# SocketIO Event Handlers
@socketio.on('connect')
def handle_connect():
    print(f'User connected: {request.sid}')

@socketio.on('disconnect')
def handle_disconnect():
    print(f'User disconnected: {request.sid}')
    # Remove user from all rooms
    for room_code, users in room_users.items():
        for username, sid in list(users.items()):
            if sid == request.sid:
                del room_users[room_code][username]
                leave_room(room_code)
                emit('user_left', {
                    'username': username,
                    'message': f'{username} left the room'
                }, room=room_code)
                break

@socketio.on('join_room')
def handle_join_room(data):
    room_code = data['room']
    username = data['username']
    
    # Join the room
    join_room(room_code)
    
    # Add user to room tracking
    if room_code not in room_users:
        room_users[room_code] = {}
    room_users[room_code][username] = request.sid
    
    # Notify other users in room
    emit('user_joined', {
        'username': username,
        'message': f'{username} joined the room'
    }, room=room_code)
    
    print(f'{username} joined room {room_code}')

@socketio.on('send_message')
def handle_message(data):
    room_code = data['room']
    message = data['message']
    username = data['username']
    timestamp = datetime.now().strftime("%I:%M %p")
    
    # Broadcast message to all users in room
    emit('receive_message', {
        'username': username,
        'message': message,
        'timestamp': timestamp
    }, room=room_code)
    
    print(f'Message in {room_code} from {username}: {message}')

@socketio.on('typing')
def handle_typing(data):
    room_code = data['room']
    username = data['username']
    is_typing = data['is_typing']
    
    # Broadcast typing status to others in room (not sender)
    emit('user_typing', {
        'username': username,
        'is_typing': is_typing
    }, room=room_code, include_self=False)

@app.route("/about")
def about_page():
    return render_template('about.html')

@app.route("/contact")
def contact_page():
    return render_template('contact.html')

if __name__ == '__main__':
    socketio.run(app, debug=True)  