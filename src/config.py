import logging
import logging.handlers
import os

import yaml


def configure_logging(data: dict):
    log_file = data['absolute_path'] if data['absolute_path'] else os.path.join(os.path.abspath(os.path.join(os.getcwd(), '..')), data['relative_path'])
    log_dir = os.path.dirname(log_file)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    logger = logging.getLogger("app_logger")
    logger.setLevel(logging.DEBUG)

    if not logger.handlers:
        rotating_handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=5 * 1024 * 1024, backupCount=2
        )

        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        rotating_handler.setFormatter(formatter)

        logger.addHandler(rotating_handler)


class ChatGptClientConfig:
    def __init__(self, system_message: str, num_responses: int, model: str, temperature: float, model_tokens_limitation: int):
        self.system_message = system_message
        self.num_responses = num_responses
        self.model = model
        self.temperature = temperature
        self.model_tokens_limitation = model_tokens_limitation

    @classmethod
    def from_yaml(cls, data: dict):
        return cls(data['system_message'], data['num_responses'], data['model'], data['temperature'], data['model_tokens_limitation'])


class TextProcessorConfig:
    def __init__(self, overlap_sentences, separators, threshold, text_processor_semaphore_size):
        self.overlap_sentences = overlap_sentences
        self.separators = separators
        self.threshold = threshold
        self.text_processor_semaphore_size = text_processor_semaphore_size

    @classmethod
    def from_yaml(cls, data: dict):
        return cls(data['overlap_sentences'], data['separators'], data['threshold'], data['text_processor_semaphore_size'])

def get_yaml_configs():
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'resources', 'application.yaml')
    with open(config_path, 'r') as f:
        configs = yaml.safe_load(f)
        return configs