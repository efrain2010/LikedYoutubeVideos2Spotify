import os
import json
import requests
import youtube_dl
from secrets import spotify_user_id, spotify_token
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
from exceptions import ResponseException

class CreatePlaylist:

    def __init__(self):
        self.youtube_client = self.get_youtube_client()
        self.all_song_info = {}

    def get_youtube_client(self):
         # Disable OAuthlib's HTTPS verification when running locally.
        # *DO NOT* leave this option enabled in production.
        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

        api_service_name = "youtube"
        api_version = "v3"
        client_secrets_file = "client_secret_177144212208-ki78h8vruc8d94kg9lfnot58h3rm2ep3.apps.googleusercontent.com.json"

        # Get credentials and create an API client
        scopes = ["https://www.googleapis.com/auth/youtube.readonly"]
        flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(client_secrets_file, scopes)
        credentials = flow.run_console()
        
        youtube_client = googleapiclient.discovery.build(api_service_name, api_version, credentials=credentials)

        return youtube_client

    def get_liked_videos(self):
        request = self.youtube_client.videos().list(
            part="snippet,contentDetails,statistics",
            myRating="like"
        )
        response = request.execute()

        #collect each video and get important info
        for item in response["items"]:
            video_title = item["snippet"]["title"]
            youtube_url = "https://www.youtube.com/watch?v={}".format(item["id"])

            #use youtube:dl to the song name & artist
            video = youtube_dl.YoutubeDL({}).extract_info(youtube_url, download=False)
            song_name=video["track"]
            artist=video["artist"]

            self.all_song_info[video_title]={
                "youtube_url":youtube_url,
                "song_name":song_name,
                "artist":artist,
                "spotify_uri":self.get_spotify_uri(song_name, artist)
            }

    def create_playlist(self):
        
        request_body = json.dumps({
            "name": "Youtube liked videos",
            "description":"All liked youtube videos",
            "public": True
        })

        query = "https://api.spotify.com/v1/users/{}/playlists".format(spotify_user_id)
        response = requests.post(
            query,
            data=request_body,
            headers= {
                "Contet-Type":"application/json",
                "Authorization":"Bearer {}".format(spotify_token)
            }
        )
        response_json = response.json()

        # playlist_id
        return response_json["id"]

    def get_spotify_uri(self, song_name, artist):
        
        print(song_name, artist)
        query = "https://api.spotify.com/v1/search?query=track%3A{}+artist%3A{}&type=track&offset=0&limit=20".format(
            song_name,
            artist  
        )
        response = requests.get(
            query, 
            headers= {
                "Contet-Type":"application/json",
                "Authorization":"Bearer {}".format(spotify_token)
            }
        )
        response_json = response.json()
        songs = response_json["tracks"]["items"]

        # only foruse first son
        return songs[0]["uri"] 

    def add_song_to_playlist(self):
        self.get_liked_videos()

        uris = [info["spotify_uri"]
                for song, info in self.all_song_info.items()]

        playlist_id = self.create_playlist()

        request_data = json.dumps(uris)

        query = "https://api.spotify.com/v1/playlists/{}/tracks".format(playlist_id)

        response = requests.post(
            query, 
            data=request_data, 
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer {}".format(spotify_token)
            }
        )

        if response.status_code != 200:
            raise ResponseException(response.status_code)

        return response.json()

if __name__ == '__main__':
    cp = CreatePlaylist()
    cp.add_song_to_playlist()