import http.server
import socketserver
import sys
import base64
import re
import os
import urllib
from http import HTTPStatus
import html
from jinja2 import Environment, FileSystemLoader
 
environment = Environment(loader=FileSystemLoader("templates/"))

PORT = '8000'
KEY = ''
ROOT = ''

def alafa_handler_from(directory):
    """alafa_handler_from can set the target directory of file server."""
    def _init(self, *args, **kwargs):
        return AlafaRquestHandler.__init__(self, *args, directory=self.directory, **kwargs)
    return type(f'HandlerFrom<{directory}>',
                (AlafaRquestHandler,),
                {'__init__': _init, 'directory': directory})

class AlafaRquestHandler(http.server.SimpleHTTPRequestHandler):
    """AlafaRequestHandler is a SimpleHTTPRequestHandler who can handle file upload with post method."""
    server_version = "SimpleHTTP/"
    def is_authenticated(self):
        """Check if is authenticated."""
        global KEY
        auth_header = self.headers['Authorization']
        print(f"auth_header is {auth_header}")
        print('Basic ' + KEY)
        return auth_header and auth_header == 'Basic ' + KEY
    def do_auth_head(self):
        """"Set authenthicaed head"""
        self.send_response(HTTPStatus.UNAUTHORIZED)
        self.send_header('WWW-Authenticate', 'Basic realm=\"Test\"')
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def try_authenticate(self):
        """"Handle authentication."""
        if not self.is_authenticated():
            self.do_auth_head()
            print("仲未认证")
            self.wfile.write(b"Not Authorization")
            return False
        return True

    def do_GET(self):
        """Serve a GET request."""
        if not self.try_authenticate():
            return
        print("已经认证")
        f = self.send_head()
        if f:
            try:
                self.copyfile(f, self.wfile)
            finally:
                f.close()


    def do_HEAD(self):
        """Serve a HEAD request."""
        f = self.send_head()
        if f:
            f.close()
 
    def do_POST(self):
        """Serve a POST request."""
        r, info = self.deal_post_data()
        print(r, info, "by: ", self.client_address)
        if r:
            result="成功"
        else:
            result="失败"
        tmpl = environment.get_template("upload_result.html")
        cont = tmpl.render(result=result, backlink=self.headers['referer'])

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html;charset=UTF-8")
        self.end_headers()
        self.wfile.write(cont.encode("utf-8"))
        
    def deal_post_data(self):
        content_type = self.headers['content-type']
        print(f"content_type  is {content_type}")
        if not content_type:
            return (False, "Content-Type header 没有包含边界符号")
        boundary = content_type.split("=")[1].encode()
        remainbytes = int(self.headers['content-length'])
        line = self.rfile.readline()
        remainbytes -= len(line)
        if not boundary in line:
            return (False, "内容没有包含边界符号")
        line = self.rfile.readline()
        remainbytes -= len(line)
        fn = re.findall(r'Content-Disposition.*name="file"; filename="(.*)"', line.decode())
        if not fn:
            return (False, "不能找到文件名")
        path = self.translate_path(self.path)
        fn = os.path.join(path, fn[0])
        line = self.rfile.readline()
        remainbytes -= len(line)
        line = self.rfile.readline()
        remainbytes -= len(line)
        try:
            out = open(fn, 'wb')
        except IOError:
            return (False, "不能创建文件，你是否有权限？")
                
        preline = self.rfile.readline()
        remainbytes -= len(preline)
        while remainbytes > 0:
            line = self.rfile.readline()
            remainbytes -= len(line)
            if boundary in line:
                preline = preline[0:-1]
                if preline.endswith(b'\r'):
                    preline = preline[0:-1]
                out.write(preline)
                out.close()
                return (True, f"文件{fn}上传成功！")
            else:
                out.write(preline)
                preline = line
        return (False, "预料之外，数据终止")

    def list_directory(self, path):
        """
        index.html不存在时，助力器生成一个目录列项。
        Return value is either a file object, or None (indicating an
        error).  In either case, the headers are sent, making the
        interface the same as for send_head().

        """
        try:
            list = os.listdir(path)
        except OSError:
            tmpl = environment.get_template("not_found_cn.html")
            cont = tmpl.render(message="你可能没有权限访问该内容。")
            self.send_response(HTTPStatus.NOT_FOUND)
            self.end_headers()
            self.wfile.write(cont.encode("utf-8"))
            return None
        list.sort(key=lambda a: a.lower())
        try:
            displaypath = urllib.parse.unquote(self.path,
                                               errors='surrogatepass')
        except UnicodeDecodeError:
            displaypath = urllib.parse.unquote(self.path)
        displaypath = html.escape(displaypath, quote=False)
        enc = sys.getfilesystemencoding()
        # print(list)
        ilist=[]
        for name in list:
            fullname = os.path.join(path, name)
            displayname = linkname = name
            # Append / for directories or @ for symbolic links
            if os.path.isdir(fullname):
                displayname = name + "/"
                linkname = name + "/"
            if os.path.islink(fullname):
                displayname = name + "@"
                # Note: a link to a directory displays with @ and links with /
            itemdict =  {
                        'href':urllib.parse.quote(linkname, errors='surrogatepass'),
                        'caption':html.escape(displayname, quote=False)
                        }
            ilist.append(itemdict)

        tmpl = environment.get_template("list_dir_cn.html")
        cont = tmpl.render(title="目录列项", itemlist=ilist)
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html;charset=UTF-8")
        self.end_headers()
        self.wfile.write(cont.encode("utf-8"))
            
        return None

def init_server():
    if len(sys.argv) !=4:
        scriptname=sys.argv[0]
        print(f"当前参数个数为 {len(sys.argv)}")
        print(f"用法： {scriptname} [端口] [用户名:秘密] [根目录]")
    else:
        global PORT, KEY, ROOT
        PORT = int(sys.argv[1])
        KEY = base64.b64encode(sys.argv[2].encode("utf-8")).decode("utf-8")
        ROOT = sys.argv[3]

        with socketserver.TCPServer(("", PORT), alafa_handler_from(ROOT)) as httpd:
            print(f"监听中 http://localhost:{PORT} | 密钥为 {KEY}")
            print("服务器已经启动，可以使用<Ctrl-C>停止服务")
            httpd.serve_forever()


if __name__ == '__main__':
    init_server()