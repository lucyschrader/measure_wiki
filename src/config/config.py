import yaml

config = {}
categories = {}


def loader():
	global config, categories
	config = load_source("config")


def load_source(source):
	loaded_data = None
	with open("src/config/{}.yaml".format(source), "r", encoding="utf-8") as f:
		loaded_data = yaml.safe_load(f)

	return loaded_data


def read_config(key):
	value = config.get(key)
	return value


def write_config(key, value):
	global config
	config[key] = value
	return key, value
