#from kivy.lang import Builder
from plyer import gps, brightness
from kivy.app import App
from kivy.properties import StringProperty
from kivy.clock import mainthread
from kivy.utils import platform
from kivy.uix.boxlayout import BoxLayout
from jnius import autoclass
from math import asin, sin, cos, sqrt, radians
#import time

# radius of the earth in meters
earth_rad = 6371000


class GpsTestApp(App):

    gps_location = StringProperty()
    text_speed = StringProperty()
    orig_volume_text = StringProperty()
    volume_text = StringProperty('80')
    old_speed = 0
    speed = 0
    old_calc_speed = 0
    calc_speed = 0
    gps_update_time = 500 #ms
    use_real_speed = True
    use_haversine_speed = False
    old_lat = None
    new_lat = None
    old_long = None
    new_long = None
    old_time = None
    new_time = None

    def request_android_permissions(self):
        """
        Since API 23, Android requires permission to be requested at runtime.
        This function requests permission and handles the response via a
        callback.
        The request will produce a popup if permissions have not already been
        been granted, otherwise it will do nothing.
        """
        from android.permissions import request_permissions, Permission

        def callback(permissions, results):
            """
            Defines the callback to be fired when runtime permission
            has been granted or denied. This is not strictly required,
            but added for the sake of completeness.
            """
            if all([res for res in results]):
                print("callback. All permissions granted.")
            else:
                print("callback. Some permissions refused.")

        request_permissions([Permission.ACCESS_COARSE_LOCATION,
                             Permission.ACCESS_FINE_LOCATION,
                             Permission.WRITE_SETTINGS], callback)
        # # To request permissions without a callback, do:
        # request_permissions([Permission.ACCESS_COARSE_LOCATION,
        #                      Permission.ACCESS_FINE_LOCATION])

    def build(self):
        try:
            gps.configure(on_location=self.on_location,
                          on_status=self.on_status)
        except NotImplementedError:
            import traceback
            traceback.print_exc()
            self.gps_status = 'GPS is not implemented for your platform'

        if platform == "android":
            print("gps.py: Android detected. Requesting permissions")
            self.request_android_permissions()
            # pyjnius for android volume
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            self.activity = PythonActivity.mActivity
            Context = autoclass('android.content.Context')
            self.audioManager = self.activity.getSystemService(Context.AUDIO_SERVICE)
            self.window = self.activity.getWindow()
            self.window_attributes = self.window.getAttributes()
            self.STREAM_MUSIC = 3
            self.original_volume = self.audioManager.getStreamVolume(self.STREAM_MUSIC)
            self.max_volume = self.audioManager.getStreamMaxVolume(self.STREAM_MUSIC)
            self.orig_volume_text = 'Original volume: '+str(self.original_volume)

    def darken_screen(self):
        brightness.set_level(1)

    def increase_orig_vol(self):
        print('Adding to original volume')
        if self.original_volume <= self.max_volume - 1:
            self.original_volume += 1
            self.update_volume(self.original_volume)
        self.orig_volume_text = 'Original volume: '+ str(self.original_volume)

    def decrease_orig_vol(self):
        print('Subtracting from original volume')
        if self.original_volume >= 1:
            self.original_volume -= 1
            self.update_volume(self.original_volume)
        self.orig_volume_text = 'Original volume: '+str(self.original_volume)

    def toggle_real_speed(self):
        if self.use_real_speed:
            self.use_real_speed = False
            print('Using virtual speed')
        else:
            self.use_real_speed = True
            print('Using real speed')
    
    def set_haversine_speed(self, val):
        self.use_haversine_speed = val
    
    def prepare_volume(self):
        print('Preparing volume')
        if self.use_haversine_speed:
            self.speed = self.calc_speed 
        self.text_speed = 'Current Speed (met/sec):\n'+ str(self.speed)
        try:
            print('Entered value: ', self.volume_text)
            base_volume_increase = int(self.volume_text)/100 * self.original_volume
            print('Base volume calculated')
            act_volume_increase = self.speed/22.4 * base_volume_increase
            new_volume = act_volume_increase + self.original_volume
            print("Calculated New Volume: ", new_volume)
            self.orig_volume_text = 'Original Volume: '+str(self.original_volume)+'\nCurrent Volume: '+str(round(new_volume, 2))
            print('About to update Volume')
            self.update_volume(new_volume)
            print('Volume has been updating')
        except ValueError:
            self.text_speed = 'Enter a valid number'

    def update_volume(self, new_volume):
        if new_volume >= self.max_volume:
            self.text_speed = 'Max volume reached'
            self.audioManager.setStreamVolume(self.STREAM_MUSIC, self.max_volume, 0)
        else:
            self.audioManager.setStreamVolume(self.STREAM_MUSIC, new_volume, 0)

    def start(self, minTime, minDistance):
        gps.start(minTime, minDistance)

    def stop(self):
        self.old_lat = None
        self.new_lat = None
        self.new_long = None
        self.old_long = None
        self.old_time = None
        self.new_time = None
        gps.stop()

    def speed_up(self):
        print('Adding to speed')
        self.speed += 1.0
        self.prepare_volume()
    
    def speed_down(self):
        print('Subtracting from speed')
        if self.speed >= 1.0:
            self.speed -= 1.0
        else:
            self.speed = 0
        self.prepare_volume()

    @mainthread
    def on_location(self, **kwargs):
        print('Location being updated')
        self.gps_location = ''
        for k, v in kwargs.items():
            self.gps_location += '\n'+k+'='+str(v)
            if k == 'speed':
                if self.use_real_speed:
                    self.old_speed = self.speed
                    self.speed = round(float(v), 3)
                    if abs(self.speed-self.old_speed) >= 5:
                        # maximum acceleration of 5 each update
                        self.speed = self.old_speed
                        self.gps_location += '\ngiven speed diff was > 5'
                    self.prepare_volume()
                break
            if k == 'lat':
                self.old_lat = self.new_lat
                self.new_lat = v
            if k == 'lon':
                self.old_long = self.new_long
                self.new_long = v
        # I already know the time, don't need to calculate it.
        # latitude and longitude are not updated every call to on_location (I think?)
        #if self.new_lat != self.old_lat and self.new_long != self.old_long:
        #    print('Position updated')
        #    self.old_time = self.new_time
        #    self.new_time = time.time()

        if self.old_lat and self.old_long and self.use_haversine_speed:
            # haversine formula (https://en.wikipedia.org/wiki/Haversine_formula)
            # latitude and longitude need to be in radians
            lat_1 = radians(self.old_lat)
            lat_2 = radians(self.new_lat)
            long_1 = radians(self.old_long)
            long_2 = radians(self.new_long)
            distance = earth_rad*asin(sqrt(sin((lat_2 - lat_1)/2)**2 + cos(lat_1)*cos(lat_2)*(sin((long_2-long_1)/2)**2)))
            delta_time = self.gps_update_time/1000
            calculated_speed = distance/delta_time
            self.old_calc_speed = self.calc_speed
            self.calc_speed = calculated_speed
            if abs(self.calc_speed-self.old_calc_speed) >= 5:
                self.calc_speed = self.old_calc_speed
                self.gps_location += '\nhaversine speed diff was > 5'
            self.gps_location += '\nhaversine speed='+str(round(calculated_speed, 2))

    @mainthread
    def on_status(self, stype, status):
        self.gps_location = 'type={}\n{}'.format(stype, status)

    def on_stop(self):
        print('App stopped')

    def on_pause(self):
        
        self.old_lat = None
        self.new_lat = None
        self.new_long = None
        self.old_long = None
        self.old_time = None
        self.new_time = None
        gps.stop()
        self.gps_location = 'No longer checking speed'
        
        print('App paused')
        return True

    def on_resume(self):
        print('App resumed')
        gps.start(self.gps_update_time, 0)
        pass

if __name__ == '__main__':
    GpsTestApp().run()