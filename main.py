import ipaddress
import pymongo
import json
import random
import re
import socket
import string
import subprocess
import time
import winrm
import nmap
import datetime

from pprint import pprint
from pydantic import BaseModel
from fastapi import FastAPI, Body, Request, Cookie
from fastapi.encoders import jsonable_encoder
from wakeonlan import send_magic_packet
from winrm.protocol import Protocol

# from fastapi.routing import Path

# from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
# from passlib.context import CryptContext
# from jose import JWTError, jwt


### APP
app = FastAPI()
# pwd_context = CryptContext(schemes=["bcrypt"])
# security = HTTPBearer()

SECRET_KEY = "l7u0BBaXkjQjqbJI2J85lOXZ24ETtiHt"
# ALGORITHM = "HS256"  # JWT
# ACCESS_TOKEN_EXPIRE_MINUTES = 30  # Time of token

# # Encrypt pass
# pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

### Const
IP_SERVER = "192.168.20.250"
SYS_USER = "pcrender\pcadmin"
SYS_PASSWD = "b@c22198@@"
RDP_TEMP = {
    "screen mode id": "i:2",
    "use multimon": "i:0",
    "desktopwidth": "i:1920",
    "desktopheight": "i:1080",
    "session bpp": "i:32",
    "winposstr": "s:0,1,0,0,920,909",
    "compression": "i:1",
    "keyboardhook": "i:2",
    "audiocapturemode": "i:0",
    "videoplaybackmode": "i:1",
    "connection type": "i:7",
    "networkautodetect": "i:1",
    "bandwidthautodetect": "i:1",
    "displayconnectionbar": "i:1",
    "enableworkspacereconnect": "i:0",
    "disable wallpaper": "i:0",
    "allow font smoothing": "i:0",
    "allow desktop composition": "i:0",
    "disable full window drag": "i:1",
    "disable menu anims": "i:1",
    "disable themes": "i:0",
    "disable cursor setting": "i:0",
    "bitmapcachepersistenable": "i:1",
    "audiomode": "i:0",
    "redirectprinters": "i:0",
    "redirectcomports": "i:0",
    "redirectsmartcards": "i:1",
    "redirectwebauthn": "i:1",
    "redirectclipboard": "i:1",
    "redirectposdevices": "i:0",
    "autoreconnection enabled": "i:1",
    "authentication level": "i:0",
    "prompt for credentials": "i:0",
    "negotiate security layer": "i:1",
    "remoteapplicationmode": "i:0",
    "alternate shell": "s:",
    "shell working directory": "s:",
    "gatewayusagemethod": "i:0",
    "gatewaycredentialssource": "i:0",
    "gatewayprofileusagemethod": "i:1",
    "promptcredentialonce": "i:1",
    "gatewaybrokeringtype": "i:0",
    "use redirection server name": "i:0",
    "rdgiskdcproxy": "i:0",
    "kdcproxyname": "s:",
    "enablerdsaadauth": "i:0",
    "drivestoredirect": "s:",
}

### CONSTANT
MONGODB_URL = "mongodb://127.0.0.1:27017/"
API_KEY = "0e7cdba83c30045082e0af5ff21c23180a862b7e32a53f2f5072ad606f95"
APP_SESSIONS = {}

### MongoDB
client = pymongo.MongoClient(MONGODB_URL)
db = client.outlook
collection_users = db.get_collection("users")
collection_devices = db.get_collection("devices")
collection_specs = db.get_collection("specs")


### Model
class UserInfo(BaseModel):
    username: str
    password: str
    ipaddress: str
    macaddress: str

    class Config:
        schema_extra = {
            "example": {
                "username": "Guest",
                "password": "Guest@gmail.com",
                "ipaddress": "192.168.2.1",
                "macaddress": "00:1B:44:11:3A:B7",
            }
        }


### Model
class Device(BaseModel):
    macaddress: str
    ipaddress: str
    group: str
    inuse: bool | None = False
    owner: str
    updatetime: str
    extip: str | None = None

    class Config:
        schema_extra = {
            "example": {
                "macaddress": "00:1B:44:11:3A:B12",
                "ipaddress": "192.168.2.1",
                "group": "G2",
                "inuse": False,
                "owner": "",
                "updatetime": "",
                "extip": "222.222.222.222:3389",
            }
        }


### Model
class Spec(BaseModel):
    group: str
    cpu: str
    ram: str
    disk: str
    gpu: str

    class Config:
        schema_extra = {
            "example": {
                "group": "00:1B:44:11:3A:B7",
                "cpu": "192.168.2.1",
                "ram": "G1",
                "disk": "SSD 1TB",
                "gpu": "GTX 1080",
            }
        }


### Model
class UpdateDevice(BaseModel):
    macaddress: str | None = None
    ipaddress: str | None = None
    group: str | None = None
    inuse: bool | None = None
    owner: str | None = None
    extip: str | None = None

    class Config:
        schema_extra = {
            "example": {
                "macaddress": "00:1B:44:11:3A:B7",
                "ipaddress": "192.168.2.1",
                "group": "G1",
                "inuse": "False",
                "owner": "UserA",
                "extip": "222.222.222.222:3389",
            }
        }


class DataModel(BaseModel):
    group: str
    user: str
    count: int


### User helper
def user_helper(user) -> dict:
    return {
        "user": user["user"],
        "password": user["password"],
        "macaddress": user["macaddress"],
    }


### Device helper
def device_helper(device) -> dict:
    return {
        "macaddress": device["macaddress"],
        "ipaddress": device["ipaddress"],
        "group": device["group"],
        "inuse": device["inuse"],
        "owner": device["owner"],
        "extip": device["extip"],
    }


### Specs helper
def spec_helper(spec) -> dict:
    return {
        "group": spec["group"],
        "cpu": spec["cpu"],
        "ram": spec["ram"],
        "disk": spec["disk"],
        "gpu": spec["gpu"],
    }


# Scan data
class ScanData(BaseModel):
    ip_range: str
    group: str


### Hash password
# class Hasher:
#     @staticmethod
#     def verify_password(plain_password, hashed_password):
#         return pwd_context.verify(plain_password, hashed_password)

#     @staticmethod
#     def get_password_hash(password):
#         return pwd_context.hash(password)

#     @staticmethod
#     def get_cookie_hash(email):
#         return pwd_context.hash(API_KEY + email)


### Response model
def ResponseModel(data, message):
    return {"data": data, "code": 200, "message": message}


def ResponseModel_Boot(data, message, password, ext_ip, int_ip, mac):
    return {
        "data": data,
        "code": 200,
        "message": message,
        "password": password,
        "ext_ip": ext_ip,
        "int_ip": int_ip,
        "mac": mac,
    }


def ErrorResponseModel(error, code, message):
    return {"error": error, "code": code, "message": message}


### WinRM template
def connect_winrm(host):
    p = Protocol(
        endpoint=f"http://{host}:5985/wsman",
        transport="ntlm",
        username="sysadmin",
        password="b@c22198@@",
        server_cert_validation="ignore",
    )
    return p


###Generate password
def generate_random_password(length: None = 8):
    characters = (
        string.ascii_letters + string.digits + string.hexdigits + string.octdigits
    )
    password = "".join(random.choices(characters, k=length))

    return password


# ###Function Get IP from MAC
# def get_ip_from_mac(mac_address):
#     arp = ARP(pdst="192.168.1.0/24")  # Thay đổi mạng tương ứng
#     ether = Ether(dst="ff:ff:ff:ff:ff:ff")  # Broadcast Ethernet frame
#     packet = ether / arp

#     result = srp(packet, timeout=3, verbose=0)[0]

#     for sent, received in result:
#         ip_address = received.psrc
#         mac_address = received.hwsrc
#         if mac_address == mac_address:
#             return ip_address

#     return None


### Wake on LAN package
@app.get("/wol/{mac_address}")
def wake_on_lan(mac_address: str):
    try:
        # BROADCAST_ADDR = "192.168.20.255"
        # # Prepare the Wake-on-LAN magic packet
        mac_address = "".join([char for char in mac_address if ord(char) < 128])

        # mac_bytes = bytes.fromhex(mac_address)
        # magic_packet = b"\xff" * 6 + mac_bytes * 16

        # # Send the magic packet to the broadcast address
        # udp_port = 9

        # for i in range(1, 3):
        #     with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        #         sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        #         sock.sendto(magic_packet, (BROADCAST_ADDR, udp_port))

        #     time.sleep(1)

        # WoL
        for i in range(1, 3):
            send_magic_packet(mac_address, interface=IP_SERVER)
            time.sleep(1)

        device = collection_devices.find_one({"macaddress": mac_address})
        if device:
            status_in_use = device["inuse"]
            if status_in_use:
                user = collection_users.find_one({"macaddress": mac_address})
                if user:
                    user_info = (
                        f"User: {user['username']}, Password: {user['password']}"
                    )
                    return ResponseModel(user_info, "User already")

        return ResponseModel("OK", f"Wake-on-LAN packet sent to {mac_address}")
    except Exception as e:
        return ErrorResponseModel("Error", 404, str(e) + ": " + mac_address)


# ###Get IP from MAC address
# @app.get("/ip/{mac_address}")
# def get_ip(mac_address: str):
#     ip_address = get_ip_from_mac(mac_address)
#     if ip_address:
#         return {"ip_address": ip_address}
#     else:
#         return {"message": f"No IP address found for MAC address {mac_address}"}


##############################################################################################################
# WinRM connection
##############################################################################################################


### Check server status
@app.get("/status/{server_ip}")
def get_server_status(server_ip: str):
    try:
        result = subprocess.run(
            ["ping", "-c", "1", "-W", "1", server_ip], capture_output=True, text=True
        )

        if result.returncode == 0:
            return ResponseModel("Server status", "on_0612")
        else:
            return ResponseModel("Server status", "off_0613")
    except Exception as e:
        return ErrorResponseModel(str(e), 400, "Error when checks server status.")


### Get hostname using winrm
@app.get("/hostname/{remote_ip}")
def get_hostname(remote_ip: str):
    try:
        ip = ipaddress.ip_address(remote_ip)
    except ValueError:
        return ErrorResponseModel({"Error", 400, "Invalid IP address"})

    try:
        if "off_0613" in str(get_server_status(remote_ip)):
            return ErrorResponseModel(
                "Server is not online", 400, "Fail_0614 when get hostname."
            )

        url = f"http://{remote_ip}:5985/wsman"

        # session = Protocol(
        #     endpoint=url, transport="ntlm", username=SYS_USER, password=SYS_PASSWD
        # )

        session = winrm.Session(
            remote_ip, auth=(SYS_USER, SYS_PASSWD), transport="ntlm"
        )
        ps_script = "hostname"

        # shell_id = session.open_shell()

        # # Chạy lệnh PowerShell từ xa
        # command_id = session.run_command(shell_id, ps_script)

        # # Đọc dữ liệu đầu ra từ lệnh
        # stdout, stderr, status_code = session.get_command_output(shell_id, command_id)
        # output = stdout.decode("utf-8").strip()

        # session.cleanup_command(shell_id, command_id)
        # session.close_shell(shell_id)

        result = session.run_cmd(ps_script)

        status_code = result.status_code
        output = result.std_out.decode("utf-8").strip()

        # In kết quả

        if status_code == 0:
            return ResponseModel(output, "Data retrived success")
        else:
            return ErrorResponseModel("Error: ", 400, "Fail_0614 when get hostname.")
        # Đóng shell và phiên kết nối
    except Exception as e:
        return ErrorResponseModel(str(e), 400, "Fail_0614 when get hostname.")


###Shutdown computer
@app.post("/shutdown/{remote_ip}")
def shutdown_server(remote_ip: str):
    try:
        ip = ipaddress.ip_address(remote_ip)
    except ValueError as v:
        return ErrorResponseModel(str(v), 404, "Invalid IP address")
    

    try:
        if "off_0613" in str(get_server_status(remote_ip)):
            updated_status_device = collection_devices.update_one(
                {"ipaddress": remote_ip}, {"$set": {"inuse": False, "owner": ""}}
            )
            return ResponseModel("OK", "Shutdown success.")

        # device_update(remote_ip)
        url = f"http://{remote_ip}:5985/wsman"
        session = winrm.Session(
            remote_ip, auth=(SYS_USER, SYS_PASSWD), transport="ntlm"
        )
        # session = Protocol(
        #     endpoint=url,
        #     transport="ntlm",
        #     username=SYS_USER,
        #     password=SYS_PASSWD,
        # )
        # cmd_clear_user = """ Get-LocalUser | Where-Object {$_.Name -ne 'sysadmin' -and $_.Name -ne 'Administrator' -and $_.Enabled -eq $true} | ForEach-Object { Remove-LocalUser -Name $_.Name } """
        cmd_shut_down = """ shutdown /s /t 0 """

        # shell_id = session.open_shell()

        # result_code_clear_user = session.run_ps(cmd_clear_user)
        result_code_shutdown = session.run_ps(cmd_shut_down)

        # # Run cmd_clear_user
        # cmd_id_clear_user = session.run_command(
        #     shell_id, "powershell", [cmd_clear_user]
        # )
        # session.cleanup_command(shell_id, cmd_id_clear_user)

        # # Run cmd_shut_down
        # cmd_id_shut_down = session.run_command(shell_id, "powershell", [cmd_shut_down])
        # session.cleanup_command(shell_id, cmd_id_shut_down)

        # # Get commnad output
        # stdout, stderr, status_code = session.get_command_output(
        #     shell_id, cmd_id_shut_down
        # )
        # output = stdout.decode("utf-8").strip()

        # session.close_shell(shell_id)
        # Print status

        if result_code_shutdown.status_code == 0:
            try:
                status_device = collection_devices.find_one({"ipaddress": remote_ip})
                if status_device:
                    time.sleep(60)
                    updated_status_device = collection_devices.update_one(
                        {"ipaddress": remote_ip}, {"$set": {"inuse": False, "owner": ""}}
                    )
                    delete_user = collection_users.delete_one(
                        {"macaddress": status_device["macaddress"]}
                    )
            except Exception as e:
                return ErrorResponseModel(
                    str(e), 404, "Error when change status device when shutdown"
                )
            return ResponseModel("OK", "Shutdown success.")
        else:
            for i in range(1, 20):
                if "off_0613" in str(get_server_status(remote_ip)):
                    return ResponseModel("OK", "Shutdown success.")
        # Close shell end disconnect
    except Exception as e:
        return ErrorResponseModel(str(e), 404, "Fail when send shutdown")
    # Change status device owner


### Notify to user
@app.post("/notify/{remote_ip}")
def notify_all_users(remote_ip: str):
    try:
        # Create a WinRM connection to the remote machine
        url = f"http://{remote_ip}:5985/wsman"  # Replace remote_ip with the actual IP address

        # session = Protocol(
        #     endpoint=url,
        #     transport="basic",
        #     username=SYS_USER,
        #     password=SYS_PASSWD,
        # )
        session = winrm.Session(
            remote_ip, auth=(SYS_USER, SYS_PASSWD), transport="ntlm"
        )
        # Construct the CMD command to send the notification to all users
        ps_script = "msg * /TIME:0 /SERVER:localhost Thời gian sử dụng còn 10 phút, quý khách vui lòng gia hạn để sử dụng hoặc sao lưu dữ liệu trước khi hết giờ. Hệ thống không lưu dữ liệu của quý khách !"

        # shell_id = session.open_shell()

        # Execute command
        # command_id = session.run(shell_id, "powershell", [ps_script])

        # Read output
        # stdout, stderr, status_code = session.get_command_output(shell_id, command_id)
        # output = stdout.decode("utf-8").strip()

        # session.cleanup_command(shell_id, command_id)
        # session.close_shell(shell_id)
        result_ps_script = session.run_cmd(ps_script)
        status_code = result_ps_script.status_code

        if status_code == 0:
            return ResponseModel("OK", "Notification sent to all users.")
        else:
            return ErrorResponseModel("Error", 404, "Fail when send notification.")

    except Exception as e:
        return ErrorResponseModel(str(e), 404, "Fail when send notification.")


""" Function in the future
### Query User
@app.get("/query-users/{remote_ip}")
def query_users(remote_ip: str):
    try:
        ip = ipaddress.ip_address(remote_ip)
    except ValueError:
        return {"error": "Invalid IP address"}

    try:
        url = f"http://{remote_ip}:5985/wsman"
        session = winrm.Session(url, auth=(username, password))

        ps_scirpt = \""" query user \"""

        result = session.run_ps(ps_scirpt)

        lines = str(result.std_out).strip().split("\\r\\n")

        # Lấy tên cột từ dòng đầu tiên
        columns = lines[0].split()

        # Xử lý dữ liệu từ các dòng còn lại
        data = []
        for line in lines[1:]:
            values = line.split()
            entry = {col: val for col, val in zip(columns, values)}
            data.append(entry)

        # Chuyển đổi thành JSON
        json_data = json.dumps(data)

        return {json_data}

    except Exception as e:
        return {"error": str(e)}
"""


### Delete user
@app.delete("/delete/")
def delete_user(userInfo: UserInfo):
    data = userInfo.dict()
    ip = str(data["ip"]).strip()
    userOS = str(data["name"]).strip()

    try:
        valid_ip = ipaddress.ip_address(ip)
    except ValueError:
        return {"error": "Invalid IP address"}

    url = f"http://{ip}:5985/wsman"

    # session = Protocol(
    #     endpoint=url, transport="basic", username=SYS_USER, password=SYS_PASSWD
    # )

    session = winrm.Session(ip, auth=(SYS_USER, SYS_PASSWD), transport="basic")
    # shell_id = session.open_shell()

    # Check user valid
    command_check_user = f"net user {userOS}"

    # command_check_user_id = session.run_cmd(
    #     shell_id, "powershell", [command_check_user]
    # )

    # stdout, stderr, status_code = session.get_command_output(
    #     shell_id, command_check_user_id
    # )
    # session.cleanup_command(shell_id, command_check_user_id)

    result_command_check_user = session.run_cmd(command_check_user)

    user_exists = (
        "The command completed successfully."
        in result_command_check_user.std_out.decode("utf-8")
    )
    user_non_exists = (
        "The user name could not be found."
        in result_command_check_user.std_err.decode("utf-8")
    )

    if user_exists:
        command_delete_user = f"net user {userOS} /delete"
        # command_delete_user_id = session.run_command(
        #     shell_id, "powershell", [command_delete_user]
        # )
        # stdout, stderr, status_code = session.get_command_output(
        #     shell_id, command_delete_user_id
        # )

        # session.cleanup_command(shell_id, command_delete_user_id)

        # output = stdout.decode("utf-8")
        # session.close_shell(shell_id)

        result_command_delete_user = session.run_cmd(command_delete_user)
        output = result_command_check_user.std_out.decode("utf-8").strip()

        return {"message": output}
    if user_non_exists:
        return {"message": f"User {userOS} non exist."}


### Boot function
@app.post("/boot/")
def boot_endpoint(data: DataModel):
    # start_time = time.time()
    try:
        # Get data from Body
        os_user = data.user
        group = data.group
        count = data.count

        devicesCount = device_count(group)

        # Check device count
        if devicesCount == 0:
            return ResponseModel("OK", "All device in use")

        if devicesCount < count:
            return ResponseModel("OK", f"Please select device less than {devicesCount}")

        # Wake all device match with limit
        for device in collection_devices.find({"group": group, "inuse": False}):
            devicesCount = device_count(group)
            devices = []
            # Generate random password
            os_password = generate_random_password(12)
            url = f"http://{device['ipaddress']}:5985/wsman"

            # Check device count
            if devicesCount == 0:
                return ResponseModel("OK", "All device in use")

            # WoL
            wol = wake_on_lan(device["macaddress"])

            collection_devices.update_one(
                {"macaddress": device["macaddress"]},
                {
                    "$set": {
                        "inuse": True,
                        "owner": f"{os_user}_waking",
                    }
                },
            )

            if wol["code"] != 200:
                collection_devices.update_one(
                    {"macaddress": device["macaddress"]},
                    {"$set": {"owner": "ERROR_MAC_INVALID"}},
                )
                devicesCount = collection_devices.count_documents(
                    {"group": group, "inuse": False}
                )
                if devicesCount == 0:
                    return ResponseModel("OK", "All device in use")
                else:
                    continue

            # Check status
            server_status = str(get_server_status(device["ipaddress"]))

            if "on_0612" in server_status:
                for i in range(1, 20):
                    winrm_status = str(get_hostname(device["ipaddress"]))
                    if "success" in winrm_status:
                        collection_devices.update_one(
                            {"macaddress": device["macaddress"]},
                            {
                                "$set": {
                                    "inuse": True,
                                    "owner": os_user,
                                }
                            },
                        )
                        break
                winrm_status = str(get_hostname(device["ipaddress"]))
                if "Fail_0614" in winrm_status:
                    collection_devices.update_one(
                        {"macaddress": device["macaddress"]},
                        {"$set": {"owner": "PC_ERROR"}},
                    )
                    devicesCount = collection_devices.count_documents(
                        {"group": group, "inuse": False}
                    )
                    if devicesCount == 0:
                        return ResponseModel("OK", "All device in use")

            else:
                start_time = time.time()
                winrm_status = ""
                for i in range(1, 300):
                    winrm_status = str(get_hostname(device["ipaddress"]))
                    if "success" in winrm_status:
                        collection_devices.update_one(
                            {"macaddress": device["macaddress"]},
                            {
                                "$set": {
                                    "inuse": True,
                                    "owner": os_user,
                                }
                            },
                        )
                        break
                    if time.time() - start_time > 210:
                        break
                if "Fail_0614" in winrm_status:
                    collection_devices.update_one(
                        {"macaddress": device["macaddress"]},
                        {"$set": {"owner": "PC_ERROR"}},
                    )
                    devicesCount = device_count(group)
                    if devicesCount == 0:
                        return ResponseModel("OK", "All device in use")

            session = winrm.Session(
                device["ipaddress"], auth=(SYS_USER, SYS_PASSWD), transport="ntlm"
            )

            command_check_user = f"net user '{os_user}'"

            result_command_check_user = session.run_cmd(command_check_user)

            stdout_command_check_user = result_command_check_user.std_out.decode(
                "utf-8"
            ).strip()
            stderr_command_check_user = result_command_check_user.std_err.decode(
                "utf-8"
            ).strip()

            user_exists = (
                "The command completed successfully." in stdout_command_check_user
            )
            user_non_exists = (
                "The user name could not be found." in stderr_command_check_user
            )

            # Check status user exist in OS
            if user_exists:
                try:
                    command_changepass_os_user = f"net user {os_user} {os_password}"

                    result_command_changepass_os_user = session.run_cmd(
                        command_changepass_os_user
                    )

                    stdout_command_changepass_os_user = (
                        result_command_changepass_os_user.std_out.decode(
                            "utf-8"
                        ).strip()
                    )
                    stderr_stdout_command_changepass_os_user = (
                        result_command_changepass_os_user.std_err.decode(
                            "utf-8"
                        ).strip()
                    )

                except Exception as e:
                    return ErrorResponseModel(
                        str(e),
                        404,
                        f"Some error when modify account on {device['ipaddress']}",
                    )

            # Check status user exist in OS
            if user_non_exists:
                try:
                    command_create_user = f"""net user {os_user} {os_password} /add && net localgroup Administrators {os_user} /add && wmic useraccount where "Name='{os_user}'" set PasswordExpires=false"""

                    result_command_create_user = session.run_cmd(command_create_user)

                    stdout_command_create_user = (
                        result_command_create_user.std_out.decode("utf-8").strip()
                    )
                    stderr_command_create_user = (
                        result_command_create_user.std_err.decode("utf-8").strip()
                    )

                except Exception as e:
                    return ErrorResponseModel(
                        str(e),
                        404,
                        f"Some error when modify account on {device['ipaddress']}",
                    )

            find_user_db = collection_users.find_one(
                {"username": os_user, "macaddress": device["macaddress"]}
            )

            # Check user exist on db
            if find_user_db:
                try:
                    update_user_db = collection_users.update_one(
                        find_user_db,
                        {"$set": {"password": os_password}},
                    )
                except Exception as e:
                    return ErrorResponseModel(
                        "An error occur when add user to DB", 404, str(e)
                    )
            else:
                try:
                    add_user_db = collection_users.insert_one(
                        {
                            "username": os_user,
                            "password": os_password,
                            "macaddress": device["macaddress"],
                        }
                    )
                    new_user_db = collection_users.find_one(
                        {"_id": add_user_db.inserted_id}
                    )
                except Exception as e:
                    return ErrorResponseModel(
                        "An error occur when update user on DB", 404, str(e)
                    )
            ### PS CMD

            # Append device to dict
            info_login = {
                "full address:s:": device["extip"],
                "username:s:": os_user,
            }
            info_login.update(RDP_TEMP)
            devices.append(info_login)

            end_time = time.time()

            # Return response model
            return ResponseModel_Boot(
                devices,
                message="Users data retrieved successfully",
                password=os_password,
                ext_ip=device["extip"],
                int_ip=device["ipaddress"],
                mac=device["macaddress"],
            )

    except Exception as e:
        return ErrorResponseModel(f"An error occured.", 400, str(e) + str(wol))


### Scan device
@app.post("/scan/{ip_range}")
def scan_and_insert(ip_range: str):
    try:
        nm = nmap.PortScanner()
        nm.scan(ip_range, arguments="-p 1-65535 -T4 -A -v")

        devices = []
        for ip, data in nm[ip_range].get("scan", {}).items():
            device = {
                "macaddress": data["addresses"].get("mac", ""),
                "ipaddress": ip,
                "group": "SELECT",
                "inuse": False,
                "owner": "blank",
                "updatetime": datetime.datetime.now(),
                "extip": "",
            }
            devices.append(device)

        # Insert devices data into MongoDB collection
        result = collection_devices.insert_many(devices)

        return {
            "message": "Devices data inserted successfully",
            "inserted_ids": result.inserted_ids,
        }
    except Exception as e:
        return {"message": "Error inserting devices data", "error": str(e)}


##############################################################################################################
# Modify user
##############################################################################################################


###Show all users
@app.get("/users/shows/")
def user_list():
    users = list(collection_users.find())

    if users:
        return ResponseModel(users, "Users data retrieved successfully")

    return ResponseModel(users, "Empty list returned")


##############################################################################################################
# Modify device
##############################################################################################################

### Check device count
@app.get("/devices/check/{group}")
def devices_check(group: str):
    try:
        devicesCount = device_count(group)
        if devicesCount > 0 :
            return ResponseModel(
                "OK",
                f"We have {devicesCount} device of group name {group}")
        else:
            return ResponseModel(
                "OK",
                f"All device in use of group name {group}")

    except Exception as e:
        return ErrorResponseModel(f"Error when get count device of group name {group}",400, str(e))

### Show all devices
@app.get("/devices/shows/")
def devices_shows():
    devices = []
    for device in collection_devices.find():
        devices.append(device_helper(device))

    if devices:
        return ResponseModel(devices, "Users data retrieved successfully")

    return ResponseModel(devices, "Empty list returned")


### Create Device
@app.post("/devices/add/")
def device_create(device: Device):
    data = jsonable_encoder(device)
    try:
        check_device = collection_devices.find_one({"macaddress": data["macaddress"]})
        if check_device:
            return {"message": f"Device with {data['macaddress']} is exist. "}
        add_device = collection_devices.insert_one(data)
        new_device = collection_devices.find_one({"_id": add_device.inserted_id})
        return ResponseModel(device_helper(data), "Device added successfully.")
    except Exception as e:
        return ErrorResponseModel("An error occur when add device", 404, str(e))


### Update Device
@app.put("/device/update/")
def device_update(req: UpdateDevice):
    data = jsonable_encoder(req)
    dataModify = {k: v for k, v in req.dict().items() if v is not None}
    try:
        device = collection_devices.find_one({"macaddress": data["macaddress"]})
        if device:
            updated_device = collection_devices.update_one(device, {"$set": dataModify})
            if updated_device:
                return ResponseModel(
                    f"Device with MAC: {data['macaddress']} update is successful",
                    "Device updated successfully",
                )

            return ErrorResponseModel(
                "An error occurred",
                404,
                "There was an error updating the device data.",
            )
        return ErrorResponseModel(data, "Update device success")
    except:
        return ErrorResponseModel("An error occurred.", 400, "Invalid request")


### Delete device
@app.delete("/devices/delete/{mac}")
def device_delete(mac: str):
    try:
        device = collection_devices.find_one({"macaddress": mac})
        if device:
            collection_devices.delete_one({"macaddress": mac})
            return ResponseModel(
                f"Device with MAC address: {mac} removed",
                "Device deleted successfully",
            )

        return ErrorResponseModel(
            "An error occurred",
            404,
            f"Device with MAC address: {mac} doesn't exist",
        )
    except Exception as e:
        return ErrorResponseModel(
            "An error occurred",
            400,
            f"Device with MAC address: {mac} is not valid".format(id),
        )


### Delete all device
@app.delete("/devices/delete-all/")
def device_delete_all():
    try:
        result = collection_devices.delete_many({})
        return {"message": f"{str(result.deleted_count)} documents deleted."}
    except Exception as e:
        return {"error": str(e)}


### Count devices
@app.get("/device/count/")
def device_count(group_id):
    try:
        regex = re.compile(group_id, re.IGNORECASE)

        number_device_count = collection_devices.count_documents({'group': {'$regex': regex}, "inuse": False})

        # device_count = collection_devices.count_documents(
        #     {"group": group_id, "inuse": False}
        # )
        return number_device_count
    except Exception as e:
        return ErrorResponseModel("Error", 400, "Fail when count device.")


##############################################################################################################
# Modify user
##############################################################################################################


### Delete all users
@app.delete("/users/delete-all/")
def users_delete_all():
    try:
        result = collection_users.delete_many({})
        return {"message": f"{str(result.deleted_count)} documents deleted."}
    except Exception as e:
        return {"error": str(e)}


##############################################################################################################
# Modify specs
##############################################################################################################


### Show all specs
@app.get("/specs/shows/")
def specs_shows():
    specs = []
    for spec in collection_specs.find():
        specs.append(spec_helper(spec))

    if specs:
        return ResponseModel(specs, "Specs data retrieved successfully")

    return ResponseModel(specs, "Empty list returned")
