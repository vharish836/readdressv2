#! bin/python
import tornado.ioloop
import tornado.web
import tornado.log
import tornado.gen
import tornado.httpclient
import tornado.websocket
import sys
import motor
import uuid
import redis
import json
import pickle
import qrcode
import base64
import io
import oath
from qrcode.image.pure import PymagingImage
from concurrent.futures import ThreadPoolExecutor

def gen_data(code):
    q = qrcode.QRCode(image_factory=PymagingImage)
    q.add_data("SMSTO:9988776655:READDR "+code)
    im = q.make_image()
    b = io.BytesIO()
    im.save(stream=b)
    data = "data:image/png;base64," + base64.b64encode(b.getvalue()).decode()
    return data

class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.set_secure_cookie("sess",uuid.uuid4().hex,httpOnly=True)
        self.render("index.html")

class SmsHandler(tornado.web.RequestHandler):
    def get(self):
        otp = self.get_argument('otp',None)
        mobile = self.get_argument('mobile',None)
        if not otp or not mobile or otp not in sockmap:
            self.set_status(400)
            self.finish()
            return
        res = {}
        res['innermodal'] = "<div class='w3-input-group'><input id='content' class='w3-input' type='text' name='addr' required><label class='w3-label w3-validate'>Address</label></div><button onclick='submitcontent()' class='w3-btn w3-indigo w3-card-4'>Submit</button>"
        res['modalhead'] = "<h5>Enter Address</h5>"
        res['type'] = "addr"
        sockmap[otp]['websock'].write_message(json.dumps(res))
        session = self.settings['redis'].get(sockmap[otp]['sess'])
        if not session:
            self.set_status(400)
            self.finish()
            return
        session = pickle.loads(session)
        session['mobile'] = mobile
        self.settings['redis'].set(sockmap[otp]['sess'],pickle.dumps(session))
        del sockmap[otp]
        self.set_status(200)
        self.finish()
        return

known_types = ['email','eotp','addr']

sockmap = {}

class WebSocketHandler(tornado.websocket.WebSocketHandler):
    def on_close(self):
        if hasattr(self,"eotp") and self.eotp in sockmap:
            tornado.log.gen_log.info('removing stale sock')
            del sockmap[self.eotp]

    @tornado.gen.coroutine
    def on_message(self,message):
        try:
            data = json.loads(message)
        except json.JSONDecodeError as e:
            tornado.log.gen_log.info("error loading json data " + str(e))
            self.close(code=1003,reason=str(e))
        tornado.log.gen_log.info(" message " + str(data))
        sess = self.get_secure_cookie('sess')
        if 'type' not in data or data['type'] not in known_types or not sess:
            self.close(code=1003,reason='invalid message type')
        sess = sess.decode()
        res = {}
        if data['type'] == 'email':
            res['innermodal'] = "<div class='w3-input-group'><input id='content' class='w3-input' type='text' name='eotp' required><label class='w3-label w3-validate'>OTP</label></div><button onclick='submitcontent()' class='w3-btn w3-indigo w3-card-4'>Submit</button>"
            res['modalhead'] = "<h5>Enter OTP received in confirmation Email</h5>"
            res['type'] = "eotp"
            self.eotp = oath.hotp(sess,1)
            # TBD: send confirmation email with eotp
            tornado.log.gen_log.info('eotp ' + self.eotp)
            session = {'actual': data['email']}
            self.settings['redis'].set(sess,pickle.dumps(session))
            self.write_message(json.dumps(res))
            return
        elif data['type'] == "eotp":
            session = self.settings['redis'].get(sess)
            if not session or not hasattr(self,"eotp"):
                self.close(code=1003,reason='Invalid Session')
            session = pickle.loads(session)
            if self.eotp == data['eotp']:
                imgdata = yield self.settings['tpool'].submit(gen_data,self.eotp)
                res['innermodal'] = "<h5 class='w3-center'>SMS READDR " + self.eotp + "<br>to 9988776655</h5><div class='w3-container w3-hide-small w3-center'><h5>OR<br>Scan the below QRCODE</h5><img class='w3-image' style='max-height: 150px;' src='" + imgdata + "'/></div><h5 class='w3-center'>The page will auto-update as soon as we receive your SMS</h5>"
                res['modalhead'] = "<h5>Send SMS to Add Phone Number</h5>"
                res['type'] = "ssms"
                sockmap[self.eotp] = {'websock': self, 'sess': sess}
                self.write_message(json.dumps(res))
            else:
                self.close(code=1003,reason='Wrong OTP')
            return
        elif data['type'] == "addr":
            session = self.settings['redis'].get(sess)
            if not session:
                self.close(code=1003,reason='Invalid Session')
            session = pickle.loads(session)
            session['address'] = data['addr']
            session['mapped'] = session['mobile'] + '@readdess.io'
            yield self.settings['db'].users.save(session)
            self.settings['redis'].delete(sess)
            self.close(code=1000)
            return

routes = [
        (r"/", MainHandler),
        (r"/signup", WebSocketHandler),
        (r"/sms", SmsHandler),
    ]

settings = {
        "static_path": "assets",
        "static_url_prefix": "/assets/",
        "template_path": "html",
        "compress_response": True,
        "cookie_secret": uuid.uuid4().hex,
        "redis": redis.StrictRedis(),
        "debug": True,
        "db": motor.MotorClient().readdressdb,
        "tpool": ThreadPoolExecutor(10),
    }

def make_app():
    return tornado.web.Application(routes,**settings)

if __name__ == "__main__":
    app = make_app()
    app.listen(8888)
    tornado.log.logging.basicConfig(stream=sys.stdout,level=tornado.log.logging.DEBUG)
    tornado.ioloop.IOLoop.current().start()
