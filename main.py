import os
import asyncio
import json
import csv
import errno
import socket
import time
import psutil

import requests
from enum import Enum
from pythonosc import udp_client, osc_server, dispatcher
from tinyoscquery.query import OSCQueryBrowser, OSCQueryClient
from tinyoscquery.queryservice import OSCQueryService, OSCAccess

"""
버전코드 설명
(메이저).(기능추가).(버그수정)(베타테그)
현재 버전: 1.2.5a

to do 
1. 파라미터 리셋기능제작 (완료)
    a. 리셋기능을 담당할 파라미터의 주소를 설정파일에 추가 (완료)
    b. 초기값 필드 csv 추가(load, save, create) (완료)
    c. 리시버에 리셋 핸들러 작성 (완료)
    
2. float / iD 만 사용하는 라이트모드 함수 및 분기 제작 (완료)
"""
Version = "1.3.2a"


class Flag(Enum):
    Info = "\033[34m[INFO]\033[0m "
    Debug = "\033[32m[Debug]\033[0m "
    Warn = "\033[33m[Warning]\033[0m "


class OSCQuery:
    @staticmethod
    def __check_process_is_running():
        """
        (PRIVATE STATIC)return true if vrc is running
        :return: (Bool) result
        """
        for proc in psutil.process_iter():
            ps_name = os.path.splitext(proc.name())[0]

            if ps_name == 'VRChat':
                return True

        return False

    def __init__(self):
        self.http_port: int = 0
        self.osc_port: int = 0
        self.vrchat_client_port = None

        if not OSCQuery.__check_process_is_running():
            print("VRC isn't running waiting...")
            while(not OSCQuery.__check_process_is_running()):
                time.sleep(1)

        # find free udp port and set osc_port
        self.__get_free_udp_port()
        # find free tcp port and set http_port
        self.__get_free_tcp_port()

        self.oscQueryService = OSCQueryService("OSC Parameter Increaser", self.http_port, self.osc_port)
        self.oscQueryService.advertise_endpoint("/avatar/parameters/MuteSelf", False, OSCAccess.WRITEONLY_VALUE)

        self.browser = OSCQueryBrowser()
        # wait for discovery
        time.sleep(2)

        while self.vrchat_client_port is None:
            for service_info in self.browser.get_discovered_oscquery():
                client = OSCQueryClient(service_info)

                if 'VRChat-Client' in client.service_info.name:
                    self.vrchat_client_port = client.service_info.port
                    print(Flag.Info.value + f"VRChat port found: {self.vrchat_client_port}")

                time.sleep(1)

    def __get_free_udp_port(self):
        """
        (PRIVATE) set udp port
        :return: NONE
        """

        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
            udp_socket.bind(('localhost', 0))
            port = udp_socket.getsockname()[1]

            self.osc_port = port

            print(Flag.Info.value + "getting UDP port has been completed")

    def __get_free_tcp_port(self):
        """
        (PRIVATE) set tcp port
        :return: NONE
        """
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as tcp_socket:
            tcp_socket.bind(('localhost', 0))
            tcp_socket.listen(1)
            port = tcp_socket.getsockname()[1]

            self.http_port = port
            print(Flag.Info.value + "getting TCP port has been completed")

    # <method that returns class variable>
    def get_osc_port(self) -> int:
        """
        get UDP port number for osc
        :return: (Int) port number for osc
        """
        return self.osc_port

    def get_http_port(self) -> int:
        """
        get TCP port number for http connection
        :return: (Int) port number for http connection
        """
        return self.http_port

    def get_current_avatar(self) -> str:
        """
        get current avatar id
        :return: (String) Avatar ID
        """

        while True:
            response = requests.get(f"http://127.0.0.1:{self.vrchat_client_port}/avatar/change")

            if response.status_code == 200:
                json_data = response.json()
                return json_data['VALUE'][0]

            time.sleep(1)

    def get_avatar_prmt(self) -> dict:
        """
        get current avatar's parameters
        :return: (Dictionary) parameters
        """
        response = requests.get(f"http://127.0.0.1:{self.vrchat_client_port}/avatar/parameters")

        if response.status_code == 200:
            prmt = response.json()
            return prmt
    # </method that returns class variable>


class Config:
    CONFIG_VERSION = 3

    def __init__(self):
        # <NETWORK>
        self.ip_addr: str = "127.0.0.1"
        self.client_port: int = 9000
        # </NETWORK>

        # <PARAMETERS>
        self.prmt_id: str = "OSCPI/id"
        self.prmt_float_out: str = "OSCPI/out/float"
        self.prmt_int_out: str = "OSCPI/out/int"
        self.prmt_bool_out: str = "OSCPI/out/bool"
        self.prmt_out_light: str = "OSCPI/out/light"

        self.prmt_reset: str = "OSCPI/reset"

        self.ignore_addr: list = ["FT", "OUT"]
        # </PARAMETERS>

        # <FILES>
        self.sheet_path: str = "./sheets"
        self.blacklist_path: str = "./blacklist.csv"
        # </FILES>

        if self.load() == errno.ENOENT:
            print(Flag.Info.value + "there's no config file. now create new one.")
            self.save()

    def load(self, _file: str = "./config.json") -> int:
        """
        load config file
        :param _file: [optional] (String) file path that have setting value (json format)
        :return: (Int) errno more information see this page https://docs.python.org/3/library/errno.html
        """
        try:
            with open(_file, 'r', encoding='utf-8') as f:
                raw = json.load(f)

                self.ip_addr = raw["NETWORK"]["ip"]
                self.client_port = raw["NETWORK"]["client_port"]

                self.prmt_id = raw['PARAMETERS']['prmt_id']
                self.prmt_float_out = raw['PARAMETERS']["prmt_float"]
                self.prmt_int_out = raw['PARAMETERS']["prmt_int"]
                self.prmt_bool_out = raw['PARAMETERS']["prmt_bool"]
                self.prmt_out_light = raw['PARAMETERS']["prmt_light"]

                self.prmt_reset = raw['PARAMETERS']['prmt_reset']

                self.ignore_addr = raw['PARAMETERS']['ignore_address']

                self.sheet_path = raw['FILES']['sheet_directory']
                self.blacklist_path = raw['FILES']['blacklist_file']

                return 0
        except IOError as e:
            return e.errno
        except Exception as e:
            raise e

    def save(self, _file: str = "./config.json") -> int:
        """
        create or update config file
        :param _file: [optional] (String) file path that config file saved
        :return: (Int) errno, You can get more information from this page https://docs.python.org/3/library/errno.html
        """

        try:
            with open(_file, "w", encoding='utf-8') as f:
                f.write(self.tojson())
                print(Flag.Info.value + '**CONFIG DATA SAVE COMPLETE**')
                return 0
        except IOError as e:
            return e.errno
        except Exception as e:
            print(e)
            raise e

    def tojson(self) -> str:
        """
        convert config class to json
        :return: (String) convert class variable to json format string
        """

        d_prmt = {
            "prmt_id": self.prmt_id,
            "prmt_float": self.prmt_float_out,
            "prmt_int": self.prmt_int_out,
            "prmt_bool": self.prmt_bool_out,
            "prmt_reset": self.prmt_reset,
            "prmt_light": self.prmt_out_light,
            "ignore_address": self.ignore_addr
        }

        d_file = {
            "sheet_directory": self.sheet_path,
            "blacklist_file": self.blacklist_path
        }

        d_net = {
            "ip": self.ip_addr,
            "client_port": self.client_port,
        }

        result = {
            "CONFIG_VERSION": self.CONFIG_VERSION,
            "NETWORK": d_net,
            "PARAMETERS": d_prmt,
            "FILES": d_file
        }

        return json.dumps(result, sort_keys=False, indent=4)

    def todict(self):
        s_json: str = self.tojson()
        return json.loads(s_json)


class AvatarConfig:
    def __init__(self):
        self.avatar_id = oscq.get_current_avatar()
        self.avatar_name = self.__get_avatar_name()
        self.avatar_prmt = oscq.get_avatar_prmt()

    def __get_avatar_name(self) -> str:
        """
        (PRIVATE) get avatar name
        :return: (String) avatar name
        """
        oscpath = os.path.expandvars(r'%localappdata%low/VRChat/VRChat/OSC/')

        for (path, dir, files) in os.walk(oscpath):
            for filename in files:
                ext = os.path.splitext(filename)
                if ext[0] == self.avatar_id:
                    avatar_file = os.path.join(path, filename)
                    with open(avatar_file, 'r', encoding='utf-8-sig') as f:
                        raw = json.load(f)
                        avatar_name = raw['name']
                        return avatar_name

    def update(self, _avatar_id: str):
        """
        update avatarConfig
        :param _avatar_id: (String) changed avatar id
        :return: None
        """
        self.avatar_id = _avatar_id
        self.avatar_name = self.__get_avatar_name()
        self.avatar_prmt = oscq.get_avatar_prmt()

    def get(self) -> tuple:
        """
        get avatar information

        return vlaue information: (id, name, parameters)
        :return: (Tuple) avatar config variables
        """
        result = (self.avatar_id, self.avatar_name, self.avatar_prmt)
        return result


class Receiver:
    @staticmethod
    def avatar_change_handler(_addr, *_args):
        """
        (STATIC) This works with dispatcher.

        update sheet when avatar changed
        :param _addr: VRC parameter address
        :param _args: VRC parameter value
        :return: NONE
        """
        sheet.save(avatar_config.avatar_name, config.sheet_path)
        avatar_config.update(_args[0])
        sheet.update(avatar_config.avatar_name)

        for k, v in sheet.dic_prmt.items():
            asyncio.gather(sender.send(v['value'], k))

        print(Flag.Debug.value + "{}: {} \033".format(_addr, _args))

    @staticmethod
    def default_handler(_addr, *_args):
        """
        (STATIC) This works with dispatcher

        update parameter that in sheet, when it's value has been changed
        :param _addr: VRC parameter address
        :param _args: VRC parameter value
        """
        prmt = _addr[19:]
        if prmt in sheet.lst_prmt:
            sheet.dic_prmt[prmt]["value"] = _args[0]
            print(Flag.Debug.value + "{}: {} \033".format(_addr, _args))

            # <SEND NORMAL MODE PARAMETERS>
            if sheet.dic_prmt[prmt]['type'] == "Bool":
                asyncio.gather(sender.send(_args[0], config.prmt_bool_out, PRINT_INFO=False))
            elif sheet.dic_prmt[prmt]['type'] == "Int":
                asyncio.gather(sender.send(_args[0], config.prmt_int_out, PRINT_INFO=False))
            else:
                asyncio.gather(sender.send(_args[0], config.prmt_float_out, PRINT_INFO=False))
            # </SEND NORMAL MODE PARAMETERS>

            # SEND LIGHT MODE PARAMETER
            if sheet.dic_prmt[prmt]['type'] == "Int":
                asyncio.gather(sender.send(float(_args[0]/255), config.prmt_out_light, PRINT_INFO=False))
            else:
                asyncio.gather(sender.send(float(_args[0]), config.prmt_out_light, PRINT_INFO=False))
            # SEND ID
            asyncio.gather(sender.send(sheet.dic_prmt[prmt]['id'], config.prmt_id, PRINT_INFO=False))

    @staticmethod
    def reset_handler(_addr, *_args):
        """
        (STATIC) This works with dispatcher

        reset avatar parameter to default, when receive reset parameter value
        :param _addr: VRC parameter address
        :param _args: VRC parameter value
        """
        if _args[0]:
            print(Flag.Info.value + "RESET AVATAR")
            for k, v in sheet.dic_prmt.items():
                asyncio.gather(sender.send(v["default"], k, PRINT_INFO=False))

    @staticmethod
    def build_dispatcher():
        """
        (STATIC) build dispatcher for receiver
        """
        d = dispatcher.Dispatcher()

        d.map("/avatar/change", Receiver.avatar_change_handler)
        d.map("/avatar/parameters/" + config.prmt_reset, Receiver.reset_handler)

        d.set_default_handler(Receiver.default_handler)

        return d

    def __init__(self, _dispatcher: dispatcher.Dispatcher, _ip: str = "127.0.0.1", _port: int = 9001):
        self.ip = _ip
        self.port = _port
        self.dispatcher = _dispatcher

        self.server = osc_server.AsyncIOOSCUDPServer(
            (self.ip, self.port),
            self.dispatcher,
            asyncio.get_event_loop()
        )

        self.transport = None
        self.protocol = None

        print(Flag.Info.value + "server has been created ({}:{})".format(self.ip, self.port))

    async def start(self):
        """
        run receiver
        :return: transport
        """
        self.transport, self.protocol = await self.server.create_serve_endpoint()

        return self.transport


class Sender:
    def __init__(self, _ip: str = "127.0.0.1", _port: int = 9000):
        """
        Create instance that Send OSC packet to server.
        :param _ip: (String) server ip address that send OSC packet
        :param _port: (Int) server ip port that send OSC packet
        """
        self.client = udp_client.SimpleUDPClient(_ip, _port)
        print(Flag.Info.value + f"Client has been created ({_ip}:{_port})")

    def update(self, _ip: str, _port: int):
        """
        Update client destination
        :param _ip: (String) server ip address that send OSC packet
        :param _port: (Int) server ip port that send OSC packet
        :return:
        """
        self.client = udp_client.SimpleUDPClient(_ip, _port)
        print(Flag.Info.value + f"Client has been updated ({_ip}:{_port})")

    async def send(self, ctx, prmt: str, path: str = "/avatar/parameters/", PRINT_INFO: bool = True):
        """
        send osc packet
        :param ctx: context to send
        :param prmt: VRC parameter name
        :param path: (Optional) parameter path
        """
        full_path = path + prmt
        self.client.send_message(full_path, ctx)

        if PRINT_INFO:
            print(Flag.Info.value + f"SEND COMPLETE prm: {prmt} - ctx: ({type(ctx)}) {ctx}")


class DataSheet:
    def __init__(self, _file: str, _path: str = None):
        self.lst_prmt: list = list()
        self.dic_prmt: dict = dict()
        self.lst_blacklist: list = [
            "GestureRight",
            "GestureLeft",
            "Viseme",
            "IsOnFriendsList",
            "EyeHeightAsMeters",
            "EyeHeightAsPercent",
            "ScaleModified",
            "ScaleFactorInverse",
            "ScaleFactor",
            "VelocityMagnitude",
            "Earmuffs",
            "Voice",
            "MuteSelf",
            "VRMode",
            "TrackingType",
            "Upright",
            "AFK",
            "Grounded",
            "AngularY",
            "VelocityZ",
            "VelocityY",
            "VelocityX",
            "GestureLeftWeight",
            "GestureRightWeight",
            "Seated",
            "InStation",
            "VRCEmote",
            "VRCFaceBlendH",
            "VRCFaceBlendV"
        ]

        if self.__load_blacklist() == errno.ENOENT:
            print(Flag.Info.value + "there's no blacklist file. now create new one.")
            self.__create_blacklist()
            self.__load_blacklist()

        self.update(_file, _path)

    def __type_enum(self, _t) -> str:
        """
        convert type character to type name
        :param _t: (String) type character from VRC
        :return: (String) type name
        """
        if _t == 'i':
            return 'Int'
        elif _t == 'f':
            return 'Float'
        elif _t == 'T':
            return 'Bool'
        else:
            return 'UNKNOWN'

    def __recursive_DFS(self, prmt: dict, writer: csv.writer, _i: int) -> int:
        """
        recursive function that write csv file.
        :param prmt: (Dictionary) data dict for searching
        :param writer: (csv.writer)
        :param _i: (Int) start index number
        :return: (Int) next index number
        """
        i = _i

        for k, v in prmt['CONTENTS'].items():
            if k in config.ignore_addr:
                continue
            if v['FULL_PATH'][19:] in self.lst_blacklist:
                continue
            if v['FULL_PATH'][19:] in list(config.todict()["PARAMETERS"].values()):
                continue

            if 'TYPE' in v:
                writer.writerow([i, v['FULL_PATH'][19:], self.__type_enum(v['TYPE']), 0, 0])
                i = i + 1
            else:
                i = self.__recursive_DFS(v, writer, i)

        return i

    def __load_blacklist(self) -> int:
        """
        load blacklist file
        :return: (Int) errno, You can get more information from this page https://docs.python.org/3/library/errno.html
        """
        try:
            with open(config.blacklist_path, 'r') as f:
                reader = csv.reader(f)

                self.lst_blacklist.clear()

                for line in reader:
                    self.lst_blacklist.append(line[0])
        except IOError as e:
            return e.errno
        except Exception as e:
            raise e
        return 0

    def __create_blacklist(self) -> int:
        """
        create new blacklist file
        :return: (Int) errno, You can get more information from this page https://docs.python.org/3/library/errno.html
        """
        try:
            with open(config.blacklist_path, 'w', newline='') as f:
                writer = csv.writer(f)
                for prmt in self.lst_blacklist:
                    writer.writerow([prmt])

                print(Flag.Info.value + "Blacklist file has been created!")
        except IOError as e:
            return e.errno
        except Exception as e:
            print(e)
        return 0

    def __filter(self, _key: str) -> bool:
        """
        (PRIVATE) return false if in blacklist
        :param _key: (String)
        :return: (Bool) result
        """
        if _key in self.lst_blacklist:
            return False
        else:
            return True

    def load(self, _file: str, _path: str = './') -> int:
        """
        Load datasheet
        :param _path: [optional] (String) file path that files are exist
        :param _file: (String) file name that to load (svc format)
        :return: (Int) errno more information see this page https://docs.python.org/3/library/errno.html

        Data sheet information: [id | parameter_name | parameter_type | saved value | default value]
        """

        try:
            file = os.path.join(_path, _file)
            with open(file, 'r') as f:
                reader = csv.reader(f)

                lst = list()
                dic = dict()
                for line in reader:
                    if line[0] == 'ID':
                        continue

                    lst.append(line[1])
                    dic[line[1]] = {
                        "id": int(line[0]),
                        "type": line[2],
                        "value": 0,
                        "default": 0
                    }

                    # load last state
                    if len(line) >= 4:
                        if line[2] == "Bool":
                            if line[3] == 'True':
                                dic[line[1]]['value'] = True
                            else:
                                dic[line[1]]['value'] = False
                        elif line[2] == "Int":
                            dic[line[1]]['value'] = int(line[3])
                        elif line[2] == "Float":
                            dic[line[1]]['value'] = float(line[3])

                    # load default value
                    if len(line) >= 5:
                        if line[2] == "Bool":
                            if line[4] == 'True':
                                dic[line[1]]['default'] = True
                            else:
                                dic[line[1]]['default'] = False
                        elif line[2] == "Int":
                            dic[line[1]]['default'] = int(line[4])
                        elif line[2] == "Float":
                            dic[line[1]]['default'] = float(line[4])

                self.lst_prmt = lst
                self.dic_prmt = dic

        except IOError as e:
            return e.errno
        except Exception as e:
            raise e
        return 0

    def create(self, _file: str, _path: str = './') -> int:
        """
        Create datasheet
        :param _path: [optional] (String) file path that files are exist
        :param _file: (String) file name that to load (svc format)
        :return: (Int) errno more information see this page https://docs.python.org/3/library/errno.html

        Data sheet information: [id | parameter_name | parameter_type | saved value | default value] 
        """

        try:
            os.makedirs(_path, exist_ok=True)
            file = os.path.join(_path, _file)
            with open(file, 'w', newline='') as f:
                prmt = avatar_config.get()[2]
                writer = csv.writer(f)

                # table header
                writer.writerow(['ID', 'Parameter Name', 'Type', 'Saved Value', 'Default Value'])

                i: int = 1
                self.__recursive_DFS(prmt, writer, 1)

                print(Flag.Info.value + 'csv file has been created!')
        except IOError as e:
            return e.errno
        except Exception as e:
            raise e
        return 0

    def save(self, _file: str, _path: str = './') -> int:
        try:
            os.makedirs(_path, exist_ok=True)
            file = os.path.join(_path, _file + '.csv')
            with open(file, 'w', newline='') as f:
                writer = csv.writer(f)

                writer.writerow(['ID', 'Parameter Name', 'Type', 'Saved Value', 'Default Value'])
                for k, v in self.dic_prmt.items():
                    writer.writerow([v['id'], k, v['type'], v['value'], v['default']])

            print(Flag.Info.value + "save csv complete")
        except IOError as e:
            print(e)
            return e.errno
        except Exception as e:
            raise e
        return 0

    def update(self, _file: str, _path: str = None):
        """
        update / initialize sheet data

        :param _file: (String) file name
        :param _path: (String) file directory path
        :return: NONE
        """
        path = _path

        if path is None:
            path = config.sheet_path

        file_name = _file + '.csv'
        if self.load(file_name, path) == errno.ENOENT:
            print(Flag.Info.value + f'{_file} not found create new one')
            self.create(file_name, path)
            self.load(file_name, path)

    def get_prmt_list(self) -> list:
        return self.lst_prmt

    def get_prmt_dict(self) -> dict:
        return self.dic_prmt


async def loop(PRINT_INFO = True):
    print(Flag.Info.value + "START SENDING OSC")

    while(True):
        for k, v in sheet.dic_prmt.items():
            if v['id'] in range(0, 256):
                # <SEND NORMAL MODE PARAMETERS>
                if v['type'] == 'Bool':
                    await sender.send(v['value'], config.prmt_bool_out, PRINT_INFO=PRINT_INFO)
                elif v['type'] == 'Int':
                    await sender.send(v['value'], config.prmt_int_out, PRINT_INFO=PRINT_INFO)
                else:
                    # default (float)
                    await sender.send(v['value'], config.prmt_float_out, PRINT_INFO=PRINT_INFO)
                # </SEND NORMAL MODE PARAMETERS>

                # SEND LIGHT MODE PARAMETER
                if v['type'] == 'Int':
                    await sender.send(float(v['value'] / 255), config.prmt_out_light, PRINT_INFO=PRINT_INFO)
                else:
                    await sender.send(float(v['value']), config.prmt_out_light, PRINT_INFO=PRINT_INFO)
                # SEND ID
                await sender.send(v['id'], config.prmt_id, PRINT_INFO=PRINT_INFO)

                await asyncio.sleep(0.1)

        if PRINT_INFO:
            print("\n")


async def main():
    d = Receiver.build_dispatcher()
    receiver = Receiver(d, config.ip_addr, oscq.get_osc_port())
    transport = await receiver.start()

    await asyncio.gather(loop(PRINT_INFO=False))

    transport.close()


# Press the green button in the gutter to run the script.

if __name__ == '__main__':
    oscq = OSCQuery()
    config = Config()

    avatar_config = AvatarConfig()
    sheet = DataSheet(avatar_config.avatar_name)

    sender = Sender()

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass

    sheet.save(avatar_config.avatar_name, config.sheet_path)
    config.save()
