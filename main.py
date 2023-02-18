from flask import Flask, request, redirect, session, render_template, jsonify
import spotipy
from spotipy import oauth2, SpotifyOAuth
import pymongo
import json
import time


app = Flask(__name__)
app.secret_key = 'hffasgsdfaiolusdftiodsuaFGVASKJLFYDgsaijyfyyasoidoUSAFDGASKJDGKjJGKJDGFJKASGKSJAsdfasfthtacfsd'

# Configure the MongoDB client
client = pymongo.MongoClient("mongodb://localhost:27017/")
db = client["whatsplaying"]
users = db["users"]

# Configure the Spotify API credentials
SPOTIPY_CLIENT_ID = '8279247b509442a097a9883a8cca50a1'
SPOTIPY_CLIENT_SECRET = 'cf92a0874adf47adba07c62f68a1c2af'
# SPOTIPY_REDIRECT_URI = 'http://wp.lndevs.uk/callback'
SPOTIPY_REDIRECT_URI = "http://localhost/callback"

sp_oauth = oauth2.SpotifyOAuth(
    SPOTIPY_CLIENT_ID,
    SPOTIPY_CLIENT_SECRET,
    SPOTIPY_REDIRECT_URI,
    scope='user-read-playback-state,user-read-currently-playing',
    cache_path='.cache'
)

def get_access_token(user_id):
    user_data = users.find_one({"_id": user_id})
    if user_data is None:
        return None
    access_token = user_data.get('access_token')
    return access_token

@app.route('/')
def home():
    user_id = session.get('user_id')
    access_token = get_access_token(user_id)
    if access_token is None:
        return render_template('not_authenticated.html')
    # Retrieve the user's current playback state from Spotify
    spotify = spotipy.Spotify(auth=access_token)
    playback_state = spotify.current_playback()
    # Render the template with the current song's data
    if playback_state is not None and playback_state['is_playing']:
        current_song = {
            'name': playback_state['item']['name'],
            'artist': playback_state['item']['artists'][0]['name'],
            'cover': playback_state['item']['album']['images'][0]['url']
        }
        return render_template('authenticated.html', current_song=current_song)
    else:
        return render_template('no_song_playing.html')

@app.route("/playing")
def playing():
    return render_template("playing.html")

# Route to retrieve the user's current song in JSON format
@app.route('/current_song')
def current_song():
    user_id = session.get('user_id')
    access_token = get_access_token(user_id)
    if access_token is None:
        return jsonify({'error': 'User not authenticated.'})
    # Retrieve the user's current playback state from Spotify
    spotify = spotipy.Spotify(auth=access_token)
    playback_state = spotify.current_playback()
    if playback_state is not None and playback_state['is_playing']:
        current_song = {
            'name': playback_state['item']['name'],
            'artist': playback_state['item']['artists'][0]['name'],
            'cover': playback_state['item']['album']['images'][0]['url']
        }
        return jsonify(current_song)
    else:
        return jsonify({'status': 'No song playing.'})

# Route to start the Spotify authorization flow
@app.route('/login')
def login():
    auth_url = sp_oauth.get_authorize_url()
    # Retrieve the user ID from Spotify
    spotify = spotipy.Spotify(auth_manager=sp_oauth)
    user = spotify.me()
    user_id = user['id']
    print("Authentication flow begun :> " + str(user_id))
    # Store the user ID in the session
    session['user_id'] = user_id
    return redirect(auth_url)


# Route to complete the Spotify authorization flow
@app.route('/callback')
def callback():
    code = request.args.get('code')
    token_info = sp_oauth.get_access_token(code)
    access_token = token_info['access_token']
    session['access_token'] = access_token
    # Store the access token in MongoDB for the current user
    users.update_one(
        {"_id": session.get("user_id")},
        {"$set": {"access_token": access_token}},
        upsert=True
    )
    return request.args


if __name__ == '__main__':
    app.run(debug=True, port=80)
