import random
import math
import struct
import wave
import os
from kivy.config import Config

# --- CONFIGURATION GRAPHIQUE ---
Config.set('graphics', 'resizable', '0')
Config.set('graphics', 'width', '400')
Config.set('graphics', 'height', '700')

# --- IMPORTS ---
from kivy.app import App
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.widget import Widget
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.properties import NumericProperty, ListProperty, BooleanProperty, ObjectProperty
from kivy.metrics import dp
from kivy.core.audio import SoundLoader
from kivy.storage.jsonstore import JsonStore
from kivy.graphics import Color, Ellipse, Rectangle, Line, Mesh
from kivy.graphics.texture import Texture
from kivy.core.window import Window 
from kivy.utils import platform

# --- GESTION DES PUBS (ADMOB - MODE SÉCURISÉ) ---
# Ce bloc empêche le jeu de planter si KivMob n'est pas installé
try:
    from kivmob import KivMob, TestIds
    IS_AD_ENABLED = True
except ImportError:
    IS_AD_ENABLED = False
    # Classe vide pour ne pas faire planter le code
    class KivMob:
        def __init__(self, id): pass
        def new_banner(self, id, top_pos=True): pass
        def request_banner(self): pass
        def show_banner(self): pass
        def new_interstitial(self, id): pass
        def request_interstitial(self): pass
        def show_interstitial(self): pass
    class TestIds:
        BANNER = ""
        INTERSTITIAL = ""

# --- COULEURS DU FASO ---
RGB_PIPE_TOP = (239, 43, 45)   # Rouge
RGB_PIPE_BOT = (0, 158, 73)    # Vert
COLOR_BIRD = (0.988, 0.82, 0.086, 1) # Jaune

# --- GENERATEURS AUDIO (Création automatique des sons) ---
def generate_audio_files():
    # 1. Musique de fond (si absente)
    if not os.path.exists('fallback_music.wav'):
        sample_rate = 44100
        duration = 4.0 
        n_frames = int(sample_rate * duration)
        with wave.open('fallback_music.wav', 'w') as f:
            f.setnchannels(1); f.setsampwidth(2); f.setframerate(sample_rate)
            data = []
            for i in range(n_frames):
                t = i / sample_rate
                freq = 220.0
                if int(t * 4) % 4 == 0: freq = 261.63 
                elif int(t * 4) % 4 == 1: freq = 329.63 
                elif int(t * 4) % 4 == 2: freq = 392.00 
                else: freq = 523.25 
                val = math.sin(2 * math.pi * freq * t) * 0.1 
                data.append(struct.pack('<h', int(val * 32767)))
            f.writeframes(b''.join(data))

    # 2. Son du Score (DING)
    if not os.path.exists('score.wav'):
        sample_rate = 44100
        duration = 0.1
        frequency = 880.0 # Note A5
        with wave.open('score.wav', 'w') as f:
            f.setnchannels(1); f.setsampwidth(2); f.setframerate(sample_rate)
            data = []
            for i in range(int(sample_rate * duration)):
                t = i / sample_rate
                val = math.sin(2 * math.pi * frequency * t) * 0.3 
                data.append(struct.pack('<h', int(val * 32767)))
            f.writeframes(b''.join(data))

# --- KIVY LANGUAGE (INTERFACE) ---
kv = '''
#:import dp kivy.metrics.dp

<FasoStar>:
    canvas:
        Color:
            rgba: 0.988, 0.82, 0.086, 0.4 
        Mesh:
            mode: 'triangle_fan'
            vertices: self.vertices
            indices: self.indices

<Pipe>:
    size_hint: None, None
    canvas:
        Color:
            rgba: 1, 1, 1, 1
        Rectangle:
            pos: self.x, self.top_y
            size: self.width, self.top_h
            texture: self.tex_top
        Rectangle:
            pos: self.x, self.y
            size: self.width, self.bottom_h
            texture: self.tex_bot
        Color:
            rgba: 0, 0, 0, 1
        Line:
            rectangle: (self.x, self.top_y, self.width, self.top_h)
            width: 1.5
        Line:
            rectangle: (self.x, self.y, self.width, self.bottom_h)
            width: 1.5
        Line:
            points: (self.x, self.top_y, self.right, self.top_y)
            width: 3
        Line:
            points: (self.x, self.bottom_h, self.right, self.bottom_h)
            width: 3

<Bird>:
    size_hint: None, None
    size: dp(45), dp(45)
    canvas.before:
        PushMatrix
        Rotate:
            angle: self.angle
            origin: self.center
    canvas:
        Color:
            rgba: root.color[0]*0.9, root.color[1]*0.9, root.color[2]*0.9, 1
        Ellipse:
            pos: self.pos
            size: self.size
        Color:
            rgba: 1, 1, 0.8, 0.6
        Ellipse:
            pos: self.x + self.width*0.1, self.y + self.height*0.25
            size: self.width*0.6, self.height*0.5
        Color:
            rgba: 0,0,0,1
        Line:
            circle: (self.center_x, self.center_y, self.width/2)
            width: 1.2
        Ellipse:
            pos: self.x + self.width*0.7, self.y + self.height*0.6
            size: dp(6), dp(6)
    canvas.after:
        PopMatrix

<FlappyGame>:
    pipe_layer: pipe_layer
    bird: bird
    
    # 1. FOND
    canvas.before:
        Color:
            rgba: 1, 1, 1, 1
        Rectangle:
            pos: self.pos
            size: self.size
            texture: self.bg_texture

    # 2. VIGNETTE SOMBRE
    canvas.after:
        Color:
            rgba: 0,0,0,0.2
        Rectangle:
            pos: self.pos
            size: self.size

    # 3. ETOILE CENTRALE
    FasoStar:
        id: bg_star
        size_hint: None, None
        size: dp(200), dp(200)
        center: self.parent.center if self.parent else (0,0)

    # 4. CALQUES DE JEU
    Widget:
        id: star_layer
    Widget:
        id: pipe_layer
    Bird:
        id: bird
        pos: dp(100), root.height / 2

    # --- INTERFACE UTILISATEUR (UI) ---

    # Score en haut
    Label:
        text: str(root.score)
        font_size: '60sp'
        pos_hint: {"center_x": 0.5, "top": 0.96}
        size_hint: None, None
        size: self.texture_size
        bold: True
        color: 1, 1, 1, 1
        outline_width: 4
        outline_color: 0, 0, 0, 1

    # Meilleur Score
    Label:
        text: "BEST: " + str(root.high_score)
        font_size: '20sp'
        pos_hint: {"right": 0.95, "top": 0.98}
        size_hint: None, None
        size: self.texture_size
        bold: True
        color: 1, 1, 1, 1
        outline_width: 2
        outline_color: 0, 0, 0, 1

    # Menu Game Over / Start
    BoxLayout:
        orientation: 'vertical'
        size_hint: 0.8, 0.4
        pos_hint: {'center_x': 0.5, 'center_y': 0.5}
        opacity: 1 if (not root.started or root.game_over) else 0
        
        Label:
            text: "FLAPPY FASO" if not root.game_over else "GAME OVER"
            font_size: '45sp'
            halign: 'center'
            bold: True
            color: 1, 0.84, 0, 1
            outline_width: 5
            outline_color: 0, 0, 0, 1
            
        Label:
            text: "Tap to Start" if not root.game_over else "Tap to Restart"
            font_size: '30sp'
            color: 1, 1, 1, 1
            bold: True
            outline_width: 3
            outline_color: 0, 0, 0, 1
'''

# --- CLASSES PYTHON ---

class FasoStar(Widget):
    vertices = ListProperty([])
    indices = ListProperty([])
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(pos=self.calculate_points, size=self.calculate_points)
        Clock.schedule_once(self.calculate_points, 0)
    def calculate_points(self, *args):
        cx, cy = self.center_x, self.center_y
        outer_radius = self.width / 2
        inner_radius = outer_radius * 0.4
        points = []
        angle_step = math.pi / 5
        current_angle = -math.pi / 2 
        points.extend([cx, cy, 0.5, 0.5]) 
        for i in range(11): 
            r = outer_radius if i % 2 == 0 else inner_radius
            x = cx + math.cos(current_angle) * r
            y = cy + math.sin(current_angle) * r
            points.extend([x, y, 0, 0])
            current_angle += angle_step
        self.vertices = points
        self.indices = list(range(12))

class Pipe(Widget):
    gap = NumericProperty(dp(170))
    top_y = NumericProperty(0)
    top_h = NumericProperty(0)
    bottom_h = NumericProperty(0)
    tex_top = ObjectProperty(None)
    tex_bot = ObjectProperty(None)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.width = dp(75)
        self.scored = False # V16 : INDISPENSABLE POUR LE SCORE CORRECT

    def set_height(self, h):
        floor_h = dp(50)
        available_h = h - self.gap - (floor_h * 2)
        if available_h < 50: available_h = 50
        rand_h = random.randint(0, int(available_h))
        self.bottom_h = floor_h + rand_h
        self.top_y = self.bottom_h + self.gap
        self.top_h = h - self.top_y

class Bird(Widget):
    angle = NumericProperty(0)
    color = ListProperty(COLOR_BIRD)

class FlappyGame(FloatLayout):
    score = NumericProperty(0)
    high_score = NumericProperty(0)
    game_over = BooleanProperty(False)
    started = BooleanProperty(False)
    velocity = NumericProperty(0)
    gravity = NumericProperty(dp(1300))
    base_jump = dp(400)
    base_speed = dp(170)
    current_speed = NumericProperty(0)
    bg_texture = ObjectProperty(None)
    pipe_tex_red = ObjectProperty(None)
    pipe_tex_green = ObjectProperty(None)
    pipes = ListProperty([])
    stars = [] 
    pipe_layer = ObjectProperty(None)
    bird = ObjectProperty(None)
    sound_music = None 
    sound_jump = None  
    sound_crash = None 
    sound_score = None 
    bg_star_x = NumericProperty(0)
    app = ObjectProperty(None)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app = App.get_running_app()
        
        # 1. GENERER LES SONS SI BESOIN
        generate_audio_files()
        
        # 2. GENERER LES TEXTURES
        self.generate_flag_bg()
        self.pipe_tex_red = self.generate_pipe_texture(RGB_PIPE_TOP)
        self.pipe_tex_green = self.generate_pipe_texture(RGB_PIPE_BOT)
        
        # 3. CHARGER L'AUDIO
        self.init_audio()
        
        # 4. SAUVEGARDE
        self.store = JsonStore('flappy_faso_data.json')
        if self.store.exists('scores'): self.high_score = self.store.get('scores')['best']
        
        Clock.schedule_once(self.delayed_init_stars)
        Clock.schedule_interval(self.update, 1.0/60.0)
        self.spawn_timer = 0
        self.bg_star_x = Window.width / 2

    def init_audio(self):
        try:
            self.sound_music = SoundLoader.load('play.mp3') or SoundLoader.load('fallback_music.wav')
            if self.sound_music:
                self.sound_music.loop = True
                self.sound_music.volume = 0.5
        except: pass

        try:
            self.sound_jump = SoundLoader.load('jump.mp3')
            self.sound_crash = SoundLoader.load('crash.mp3')
            self.sound_score = SoundLoader.load('score.wav') 
        except: pass

    def play_sound(self, sound):
        try:
            if sound:
                if sound == self.sound_crash:
                    sound.volume = 1.0
                elif sound == self.sound_jump:
                    sound.volume = 0.2
                    if sound.state == 'play': sound.stop()
                else: # Score
                    sound.volume = 0.6
                    if sound.state == 'play': sound.stop()
                sound.play()
        except: pass

    def generate_pipe_texture(self, base_rgb):
        width = 64
        tex = Texture.create(size=(width, 1), colorfmt='rgb')
        buf = []
        r_base, g_base, b_base = base_rgb
        for i in range(width):
            ratio = i / (width - 1)
            # Effet 3D simple
            if ratio < 0.2: factor = 0.5 + (ratio * 2.5)
            elif ratio < 0.4: 
                h = (ratio - 0.2) * 5
                r_base, g_base, b_base = [c + (255-c)*h for c in base_rgb]
                factor = 1
            else: factor = 1.0 - ((ratio - 0.4) * 0.8)
            buf.extend([int(r_base * factor), int(g_base * factor), int(b_base * factor)])
        tex.blit_buffer(bytes(buf), colorfmt='rgb', bufferfmt='ubyte')
        return tex

    def generate_flag_bg(self):
        tex = Texture.create(size=(1, 64), colorfmt='rgb')
        buf = []
        for i in range(64):
            # Moitié Vert / Moitié Rouge
            if i < 32: buf.extend([0, 158, 73])
            else: buf.extend([239, 43, 45])
        tex.blit_buffer(bytes(buf), colorfmt='rgb', bufferfmt='ubyte')
        tex.mag_filter = 'nearest'
        self.bg_texture = tex

    def delayed_init_stars(self, dt): self.init_stars()

    def init_stars(self):
        self.stars = []
        w = Window.width if Window.width > 100 else 800
        h = Window.height if Window.height > 0 else 600
        for _ in range(40):
            self.stars.append({
                'x': random.randint(0, int(w)), 'y': random.randint(0, int(h)),
                'size': random.uniform(dp(2), dp(5)), 'depth': random.choice([0.5, 0.8, 1.2]) 
            })

    def draw_stars(self):
        if not self.ids.star_layer: return
        canvas = self.ids.star_layer.canvas
        canvas.clear()
        with canvas:
            Color(1, 1, 1, 0.7)
            for s in self.stars: Ellipse(pos=(s['x'], s['y']), size=(s['size'], s['size']))

    def update_stars(self, dt):
        w = self.width if self.width > 0 else Window.width
        h = self.height if self.height > 0 else Window.height
        for s in self.stars:
            s['x'] -= (20 * s['depth']) * dt 
            if self.started and not self.game_over: s['x'] -= (self.current_speed * 0.1 * s['depth']) * dt
            if s['x'] < 0: s['x'] = w; s['y'] = random.randint(0, int(h))

    def update_flag_star(self, dt):
        if self.started and not self.game_over:
            self.bg_star_x -= self.current_speed * 0.15 * dt
            if self.bg_star_x < -dp(150): self.bg_star_x = self.width + dp(150)
            self.ids.bg_star.center_x = self.bg_star_x
        else:
            if not self.started:
                 self.ids.bg_star.center_x = self.width / 2
                 self.bg_star_x = self.width / 2

    def on_touch_down(self, touch):
        if self.sound_music and self.sound_music.state != 'play':
            self.sound_music.play()

        if self.game_over: self.reset()
        else:
            if not self.started: 
                self.started = True; self.current_speed = self.base_speed; self.spawn_timer = 0
                if self.app.ads: self.app.ads.show_banner()
            
            self.velocity = self.base_jump
            self.play_sound(self.sound_jump)

    def reset(self):
        self.pipe_layer.clear_widgets(); self.pipes = []; self.bird.pos = (dp(100), self.height / 2)
        self.bird.angle = 0; self.velocity = 0; self.score = 0; self.game_over = False
        self.started = False; self.current_speed = self.base_speed; self.spawn_timer = 0
        self.bg_star_x = self.width / 2
        if self.sound_music and self.sound_music.state != 'play': self.sound_music.play()
        if self.app.ads: self.app.ads.request_interstitial()

    def spawn_pipe(self):
        p = Pipe(tex_top=self.pipe_tex_red, tex_bot=self.pipe_tex_green)
        p.set_height(self.height); p.x = self.width
        self.pipe_layer.add_widget(p); self.pipes.append(p)

    def update_difficulty(self):
        THRESHOLD = 5
        if self.score < THRESHOLD: self.current_speed = self.base_speed; return
        points_over = self.score - THRESHOLD
        target_speed = self.base_speed + (points_over * dp(5.0)) 
        max_speed = dp(450)
        if target_speed > max_speed: target_speed = max_speed
        self.current_speed = target_speed

    def update(self, dt):
        self.update_stars(dt); self.draw_stars()
        self.update_flag_star(dt)
        if not self.started or self.game_over: return
        self.velocity -= self.gravity * dt; self.bird.y += self.velocity * dt
        target_angle = self.velocity * 0.12; self.bird.angle = max(min(target_angle, 45), -60)
        self.spawn_timer += dt
        
        spawn_interval = dp(320) / self.current_speed
        if self.spawn_timer > spawn_interval: self.spawn_pipe(); self.spawn_timer = 0
        
        for p in self.pipes[:]:
            p.x -= self.current_speed * dt

            # --- V16: LOGIQUE DE SCORE CORRIGÉE ---
            # Si le tuyau dépasse l'oiseau et qu'on n'a pas encore marqué
            if p.right < self.bird.x and not p.scored:
                self.score += 1
                p.scored = True
                self.play_sound(self.sound_score)
                self.update_difficulty()

            # Suppression si hors écran
            if p.right < 0:
                self.pipe_layer.remove_widget(p)
                self.pipes.remove(p)
                continue
            
            # Collisions
            bird_pad = dp(8) 
            if (self.bird.right - bird_pad > p.x + dp(5)) and (self.bird.x + bird_pad < p.right - dp(5)):
                if (self.bird.y + bird_pad < p.bottom_h) or (self.bird.top - bird_pad > p.top_y):
                    self.game_over_sequence()
                    
        if self.bird.y < 0 or self.bird.top > self.height: self.game_over_sequence()

    def game_over_sequence(self):
        if not self.game_over:
            if self.sound_music and self.sound_music.state == 'play': self.sound_music.stop()
            self.play_sound(self.sound_crash)
            self.game_over = True
            if self.score > self.high_score: self.high_score = self.score; self.store.put('scores', best=self.high_score)
            if self.app.ads and random.random() > 0.5:
                self.app.ads.show_interstitial()

class FlappyApp(App):
    ads = ObjectProperty(None)
    def build(self):
        Window.clearcolor = (0,0,0,1)
        APP_ID = "ca-app-pub-3940256099942544~3347511713" 
        if IS_AD_ENABLED:
            self.ads = KivMob(APP_ID)
            self.ads.new_banner(TestIds.BANNER, top_pos=False) 
            self.ads.new_interstitial(TestIds.INTERSTITIAL)
            self.ads.request_banner()
            self.ads.request_interstitial()
        Builder.load_string(kv)
        return FlappyGame()

if __name__ == '__main__':
    FlappyApp().run()

