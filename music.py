import youtube_dl
from threading import Thread
from time import sleep
import os
import subprocess
from uuid import uuid4 as random_token

all_filenames = []

ydl_opts = {
    'format': 'bestaudio/best',
    'get-url': True,
    'get-title': True,
    'get-thumbnail': True,
    'skip-download': True,
    'get-duration': True,
    'ignore-errors': True,
    #'quiet': True
}

def check_by_youtube_dl(url):
    try:
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(url, download=False)
    except:
        return None

class DLParser(Thread):
    def __init__(self, url, queue, voice_client):
        Thread.__init__(self)
        self.url = url
        self.queue = queue
        self.voice_client = voice_client

    def run(self):
        res = check_by_youtube_dl(self.url)
        if res:
            if 'entries' in res:
                for item in res['entries']:
                   self.queue.add(QueueItem(item, self.voice_client))
            else:
                self.queue.add(QueueItem(res, self.voice_client))
                
class QueueItem:
    def __init__(self, info, voice_client):
        self.page = info['webpage_url']
        self.voice_client = voice_client
        self.player = None
        self.url = None
        self.title = None
        self.duration = None
        self.thumbnail = None
        self.filename = None
        self.generate_filename()
        self.load(info)
        self.download()

    def exit(self):
        self.player.stop()
        self.delete()
        
    def delete(self):
        if self.file_is_exists():
            try:
                os.remove(self.filename)
            except PermissionError:
                sleep(0.1)
                self.delete()

    def file_is_exists(self):
        return self.filename and os.path.isfile(self.filename)
            
    def load(self, info):
        self.url = info['url']
        self.title = info['title']
        self.duration = info['duration']
        self.thumbnail = info['thumbnail']

    def generate_filename(self):
        filename = '{}.wav'.format(random_token())
        while os.path.isfile(filename) or filename in all_filenames:
            filename = '{}.wav'.format(random_token())
        all_filenames.append(filename)
        self.filename = filename
     
    def download(self):
        subprocess.Popen([
            'ffmpeg',
            '-i', self.url,
            '-vn',
            '-acodec', 'adpcm_ima_wav',
            self.filename
        ], stderr=subprocess.DEVNULL).wait()
        
    def reload(self):
        self.load(check_by_youtube_dl(self.page))

    def file_checker(self):
        if not self.file_is_exists():
            self.download()
            if not self.file_is_exists():
                self.reload()
                self.download()
                if not self.file_is_exists():
                    return False
        return True
        
    def set_player(self, vol):
        if self.file_checker():
            self.player = self.voice_client.create_ffmpeg_player(self.filename)
            self.player.volume = vol
            return True
        else:
            return False

    def __repr__(self):
        return '`{}`({})'.format(self.title, self.duration)

class QueueController(Thread):
    def __init__(self, server_id, volume=1.):
        Thread.__init__(self)
        self.queue = []
        self.wait = 3
        self.server_id = server_id
        self.volume = volume
   
    def add(self, item):
        self.queue.append(item)

    def find_by_url(self, url, voice_client):
        DLParser(url, self, voice_client).start()
    
    def go_next(self, anyway):
        if self.queue and (self.queue[0].player or anyway):
            self.queue[0].exit()
            self.queue.pop(0)
        if self.queue:
            return self.queue[0]
        else:
            None
    
    def play_next(self, anyway=True):
        next_ = self.go_next(anyway)
        if next_:
            if next_.set_player(self.volume):
                next_.player.start()
            else:
                self.play_next(anyway)
       
    def run(self):
        while True:
            if self.queue:
                if not self.queue[0].player or self.queue[0].player.is_done():
                    self.play_next(anyway=False)
            sleep(self.wait)

    def update_voice_client(voice_client):
        for one in self.queue:
            one.voice_client = voice_client
    
    def the_last(old):
        def new(self, *args):
            if self.queue:
                return old(self, self.queue[0], *args)
        return new
    
    @the_last
    def play(self, last):
        last.player.resume()

    @the_last
    def pause(self, last):
        last.player.pause()

    @the_last
    def set_volume(self, last, vol):
        self.volume = vol
        last.player.volume = vol

    @the_last
    def stop(self, last):
        self.queue.clear()
        last.player.stop()

class MusicController:
    def __init__(self, db=None):
        self.db = db
        self.channels = {}
    
    def get_channel(self, server_id):
        channel = self.channels.get(server_id)
        if not channel:
            channel = QueueController(server_id)
            self.channels[server_id] = channel
            channel.start()
        return channel

    def put_channel(old):
        def new(self, server_id, *args):
            return old(self, self.get_channel(server_id), *args)
        return new

    @put_channel
    def find(self, channel, voice_client, url):
        channel.find_by_url(url, voice_client)

    @put_channel
    def play(self, channel):
        channel.play()

    @put_channel
    def pause(self, channel):
        channel.pause()

    @put_channel
    def skip(self, channel):
        channel.play_next()

    @put_channel
    def volume(self, channel, vol):
        channel.set_volume(vol)

    @put_channel
    def stop(self, channel):
        channel.stop()

    @put_channel
    def get_titles(self, channel):
        return [one.title for one in channel.queue]
