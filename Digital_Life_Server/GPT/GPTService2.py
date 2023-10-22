import logging
import os
import time

import GPT.machine_id
import GPT.tune as tune


class GPTService():
    def __init__(self):
        logging.info('Initializing ChatGPT Service...')
        self.chatVer = 3

        self.tune = tune.get_tune()

        self.counter = 0

        if self.chatVer == 3:
            from revChatGPT.V3 import Chatbot
            logging.info('you have your own api key. Great.')
            api_key = "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"

            self.chatbot = Chatbot(
                api_key=api_key, system_prompt=self.tune)
            logging.info('API Chatbot initialized.')

    def ask(self, text):
        stime = time.time()
        if self.chatVer == 3:
            prev_text = self.chatbot.ask(text)
        logging.info('ChatGPT Response: %s, time used %.2f' %
                     (prev_text, time.time() - stime))
        return prev_text

    def ask_stream(self, text):
        prev_text = ""
        complete_text = ""
        stime = time.time()
        asktext = text
        self.counter += 1
        # 抓取gpt輸出的文字
        for data in self.chatbot.ask(asktext) if self.chatVer == 1 else self.chatbot.ask_stream(text):
            message = data["message"][len(
                prev_text):] if self.chatVer == 1 else data

            if ("。" in message or "！" in message or "？" in message or "\n" in message) and len(complete_text) > 3:
                complete_text += message
                logging.info('ChatGPT Stream Response: %s, @Time %.2f' %
                             (complete_text, time.time() - stime))
                yield complete_text.strip()  # return part of the complete_text
                complete_text = ""
            else:
                complete_text += message

            prev_text = data["message"] if self.chatVer == 1 else data

        if complete_text.strip():
            logging.info('ChatGPT Stream Response: %s, @Time %.2f' %
                         (complete_text, time.time() - stime))
            yield complete_text.strip()
