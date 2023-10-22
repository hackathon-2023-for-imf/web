import argparse
import os
import socket
import time
import logging
import traceback
from logging.handlers import TimedRotatingFileHandler
import socket

import librosa
import requests
import soundfile
import pyodbc
import wave

import GPT.tune
from utils.FlushingFileHandler import FlushingFileHandler
from GPT import GPTService2
from TTS import TTService
from SentimentEngine import SentimentEngine
from azure.identity import DefaultAzureCredential

console_logger = logging.getLogger()
console_logger.setLevel(logging.INFO)
FORMAT = '%(asctime)s %(levelname)s %(message)s'
console_handler = console_logger.handlers[0]
console_handler.setFormatter(logging.Formatter(FORMAT))
console_logger.setLevel(logging.INFO)
file_handler = FlushingFileHandler(
    "log.log", formatter=logging.Formatter(FORMAT))
file_handler.setFormatter(logging.Formatter(FORMAT))
file_handler.setLevel(logging.INFO)
console_logger.addHandler(file_handler)
console_logger.addHandler(console_handler)


def str2bool(v):
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Unsupported value encountered.')


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--chatVer", type=int, nargs='?', required=True)
    parser.add_argument("--APIKey", type=str, nargs='?', required=False)
    parser.add_argument("--email", type=str, nargs='?', required=False)
    parser.add_argument("--password", type=str, nargs='?', required=False)
    parser.add_argument("--accessToken", type=str, nargs='?', required=False)
    parser.add_argument("--proxy", type=str, nargs='?', required=False)
    parser.add_argument("--paid", type=str2bool, nargs='?', required=False)
    parser.add_argument("--model", type=str, nargs='?', required=False)
    parser.add_argument("--stream", type=str2bool, nargs='?', required=True)
    parser.add_argument("--character", type=str, nargs='?', required=True)
    parser.add_argument("--ip", type=str, nargs='?', required=False)
    parser.add_argument("--brainwash", type=str2bool,
                        nargs='?', required=False)
    return parser.parse_args()


class Server():
    def __init__(self):
        # SERVER STUFF
        self.addr = None
        self.conn = None
        logging.info('Initializing Server...')
        self.host = socket.gethostbyname(socket.gethostname())
        self.port = 38438
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 10240000)
        self.s.bind((self.host, self.port))
        self.tmp_recv_file = 'server_received.wav'
        self.tmp_proc_file = 'server_processed.wav'

        # hard coded character map
        self.char_name = {
            'paimon': ['TTS/models/paimon6k.json', 'TTS/models/paimon6k_390000.pth', 'character_paimon', 1],
            'yunfei': ['TTS/models/yunfeimix2.json', 'TTS/models/yunfeimix2_53k.pth', 'character_yunfei', 1.1],
            'catmaid': ['TTS/models/catmix.json', 'TTS/models/catmix_107k.pth', 'character_catmaid', 1.2]

        }

        # PARAFORMER
        #self.paraformer = ASRService.ASRService('./ASR/resources/config.yaml')

        # CHAT GPT
        self.chat_gpt = GPTService2.GPTService()

        # TTS
        self.tts = TTService.TTService(*self.char_name["paimon"])

        # Sentiment Engine
        self.sentiment = SentimentEngine.SentimentEngine(
            'SentimentEngine/models/paimon_sentiment.onnx')

    def listen(self):
        # MAIN SERVER LOOP
        id_count = 0
        while True:
            try:
                text = s.get_prompt(id_count)
                if text is None:
                    continue
                id =text[0]
                user_id = text[1]
                prompt = text[2]
                for sentence in self.chat_gpt.ask_stream(prompt):
                    self.send_voice(sentence)  # 判斷每一句的情感
                #id = sentence[0]
                #user_id = sentence[1]
                #text = sentence[2]
                #end_s = sentence[3]
                #self.send_voice(text, id, id_count)  # 判斷每一句的情感
                self.notice_stream_end()
                logging.info('Stream finished.')
                id_count+=1
            except Exception as e:
                logging.error(e.__str__())
                logging.error(traceback.format_exc())
                break

    def notice_stream_end(self):
        time.sleep(0.5)
        #print('stream_finished')

    # takes text input, converts it to voice, possibly determines the sentiment of the text
    def send_voice(self, resp_text):
        self.tts.read_save(resp_text, self.tmp_proc_file,
                           self.tts.hps.data.sampling_rate)
        senti = self.sentiment.infer(resp_text)
        with wave.open(self.tmp_proc_file, 'rb') as wav_file:
            # Get the sample rate
            sample_rate = wav_file.getframerate()

            # Get the audio data as a bytes object
            audio_data = wav_file.readframes(wav_file.getnframes())
            # Get the audio format
            format = "WAV"  # Since you mentioned the format is WAV
        self.insert_data(audio_data, sample_rate, format, senti)
        time.sleep(0.5)
        logging.info("finished voice process and sentimental analysis")

    def __receive_file(self):
        file_data = b''
        while True:
            data = self.conn.recv(1024)
            # print(data)
            self.conn.send(b'sb')
            if data[-2:] == b'?!':
                file_data += data[0:-2]
                break
            if not data:
                # logging.info('Waiting for WAV...')
                continue
            file_data += data

        return file_data

    def fill_size_wav(self):
        with open(self.tmp_recv_file, "r+b") as f:
            # Get the size of the file
            size = os.path.getsize(self.tmp_recv_file) - 8
            # Write the size of the file to the first 4 bytes
            f.seek(4)
            f.write(size.to_bytes(4, byteorder='little'))
            f.seek(40)
            f.write((size - 28).to_bytes(4, byteorder='little'))
            f.flush()

    def process_voice(self):
        # stereo to mono
        self.fill_size_wav()
        y, sr = librosa.load(self.tmp_recv_file, sr=None, mono=False)
        y_mono = librosa.to_mono(y)
        y_mono = librosa.resample(y_mono, orig_sr=sr, target_sr=16000)
        soundfile.write(self.tmp_recv_file, y_mono, 16000)
        text = self.paraformer.infer(self.tmp_recv_file)

        return text

    def connect_to_azure_sql(self):
        server_name = 'ettodayserver.database.windows.net'
        database_name = 'news'
        username = 'group7'
        password = 'Ettoday@'
        port = 1433  # Replace with your custom port if it's not the default 1433

        # Azure AD authentication with DefaultAzureCredential
        credentials = DefaultAzureCredential()

        try:
            # Create a connection string
            connection_string = f'DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={server_name},{port};DATABASE={database_name};UID={username};PWD={password}'

            # Create a connection to the database
            conn = pyodbc.connect(connection_string)

            # Create a cursor object
            cursor = conn.cursor()

            return conn, cursor
        except Exception as e:
            logging.info(f"Error: {str(e)}")
            return None, None

    def get_prompt(self, id_count):
        conn, cursor = self.connect_to_azure_sql()
        print("successful connectoin")
        if conn and cursor:
            try:
                query = 'SELECT * FROM Prompt WHERE Id = ?;'
                cursor.execute(query, id_count+1)
                result = cursor.fetchall()
                for row in result:
                    sentence = row
                logging.info(sentence)
                return sentence
            except Exception as e:
                print(f"Error executing query: {str(e)}")
            finally:
                cursor.close()
                conn.close()

    def insert_data(self, audio, sample_rate, format, sentiment):
        conn, cursor = self.connect_to_azure_sql()
        if conn and cursor:
            try:
                query = "INSERT INTO Voice (audio, sample_rate, format, sentiment) VALUES (?, ?, ?, ?)"
                cursor.execute(query, (audio, sample_rate, format, sentiment))
                conn.commit()  
                logging.info("finished insertion")
            except Exception as e:
                print(f"Error executing query: {str(e)}")
            finally:
                cursor.close()
                conn.close()
    def get_local_ip(self):
        try:
            # Create a socket object
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

            # Connect to a remote server (doesn't have to be a real server)
            s.connect(("8.8.8.8", 80))  # Using Google's public DNS server as an example

            # Get the local IP address
            local_ip = s.getsockname()[0]

            # Close the socket
            s.close()

            return local_ip
        except socket.error as e:
            return "Could not determine local IP address"

if __name__ == '__main__':
    try:
        #args = parse_args()
        s = Server()
        #ip = s.get_local_ip()
        #logging.info(ip)
        s.listen()
    except Exception as e:
        logging.error(e.__str__())
        logging.error(traceback.format_exc())
        raise e
