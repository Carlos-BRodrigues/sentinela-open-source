# Sentinel-telegram
 Developed for Public Agency, University of Virginia

## How to use this scraper

1. Make a copy of `config_example.json` and rename it `config.json`;
2. Configure your MySQL database address in the `config.json` file;
3. Run the `run_configuration.py` script and verify that the tables have been created;
4. To obtain the Telegram API keys, go to my.telegram.org and register the device number;
5. Request the creation of a Desktop application and fill out the form stating the purpose of the tool;
6. Fill in the `config.json` file with the details provided (id and hash);
7. Also fill in the table in the database for that user with the phone number and name registered in `config.json`;
8. Run the `get_groups.py` script and then the `get_new_messages.py` script;
