from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager # use pip install webdriver_manager
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import StaleElementReferenceException
from time import sleep
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.by import By
import multiprocessing
import random



global buttons
buttons = ["Keep", "Discard", "paul", "john", "george", "ringo"]
options = webdriver.ChromeOptions()

global new_player
def new_player(room_name, player_name):
    driver_player_name = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options = options)
    driver_player_name.get('http://localhost:5173/')

    sleep(2)
    join_room_panel = driver_player_name.find_element('xpath', '//button[contains(@class, "join-room-panel")]')
    sleep(2)
    join_room_panel.click()
    sleep(1)

    player_username = driver_player_name.find_element('xpath', '//input[contains(@class, "join-room-me")]')
    player_room_name = driver_player_name.find_element('xpath', '//input[contains(@class, "join-room-game")]')

    sleep(5)
    driver_player_name.maximize_window()
    player_username.send_keys(player_name)
    player_room_name.send_keys(room_name)
    sleep(2)
    join_room = driver_player_name.find_element('xpath', '//button[contains(@class, "join-room-join")]')
    join_room.click()
    while True:
        
        try: 
            game_end_text_player = driver_player_name.find_element("xpath",'//h3[contains(text(),"Game Finished")]')
            if game_end_text_player.text == "Game Finished":
                break
        except NoSuchElementException:
            pass

        try:
            
            player_choice = player_name
            while (player_choice == player_name):
                player_choice = random.choice(buttons)

            
            
                
                
            # driver_player_name.refresh()
            # sleep(10)
            player_choice_button = driver_player_name.find_element("xpath",'//button[contains(text(),"{}")]'.format(player_choice))
            player_card_text = driver_player_name.find_element("xpath",'//div[contains(@class,"card-text")]'.format(player_choice))
            tgb = driver_player_name.find_element("xpath",'//h3[contains(text(),"Countdown to Chaos")]') 
            sleep(3)
            
            print(str(player_name) + " sends the card to " + str(player_choice))
            print("the card text is: " + str(player_card_text.text))
            print(str(tgb.text))
            player_choice_button.click()
            sleep(5)
            


        except NoSuchElementException:
            sleep(1)
            # print(str(player_name) + " be waiting")
            continue
        except StaleElementReferenceException:
            sleep(1)
            # print(str(player_name) + " be waiting")
            continue
    
    sleep(5)
    driver_player_name.quit()

if __name__ == '__main__' :
    
    # initiate the driver for chrome
    driver_john = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options = options)
    sleep(2)





    driver_john.get('http://localhost:5173/')
    sleep(5)

    try:
        
        create_room_panel = driver_john.find_element('xpath', '//button[contains(@class, "create-room-panel")]')
        sleep(2)
        create_room_panel.click()
        sleep(1)
        
        john_username = driver_john.find_element('xpath', '//input[contains(@class, "new-room-you")]')
        player_count = driver_john.find_element('xpath', '//input[contains(@class, "new-room-player-count")]')


        sleep(5)

        john_username.send_keys("john")
        player_count.send_keys("4")

        sleep(2)
        driver_john.maximize_window()
        create_room = driver_john.find_element('xpath', '//button[contains(@class, "new-room-create")]')
        create_room.click()
        sleep(10)

        # page = driver_john.current_url
        # driver_john.get()

        room_name = driver_john.find_element('xpath', '//h4[contains(@class, "room-name")]') 
        sleep(2)
        room_name = room_name.text
        print("The room name is: " + str(room_name))
        sleep(2)

        # driver_paul = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options = options)
        p_paul = multiprocessing.Process(target = new_player, args = [room_name,"paul"])
        p_george = multiprocessing.Process(target = new_player, args = [room_name,"george"])
        p_ringo = multiprocessing.Process(target = new_player, args = [room_name,"ringo"]) 
        p_paul.start()
        p_george.start()
        p_ringo.start()
        
        print('parallel function executing')
        while True:
            try: 
                game_end_text = driver_john.find_element("xpath",'//h3[contains(text(),"Game Finished")]')
                if game_end_text.text == "Game Finished":
                    break
            except NoSuchElementException:
                pass
                
            try:
                # driver_john.find_element('xpath','//div[contains(text(),"Its john\'s turn now")]')
                john_choice = "john"
                while(john_choice == "john"):

                    john_choice = random.choice(buttons)
                

                    
                # driver_john.refresh()
                # sleep(10)
                
                player_choice_button = driver_john.find_element("xpath",'//button[contains(text(),"{}")]'.format(john_choice))
                card_text = driver_john.find_element("xpath",'//div[contains(@class,"card-text")]'.format(john_choice))
                tgb = driver_john.find_element("xpath",'//h3[contains(text(),"Countdown to Chaos")]') 
                sleep(3)
                print("john sends the card to " + str(john_choice))
                print("the card text is: " + str(card_text.text))
                print(str(tgb.text))
                player_choice_button.click()
                sleep(5)
            except NoSuchElementException:
                sleep(1)
                # print("john be waiting")
                continue
            except StaleElementReferenceException:
                sleep(1)
                # print("john be waiting")
                continue
        sleep(15)
        p_george.join()
        p_paul.join()
        p_ringo.join()
        sleep(15)
        # global_bias = driver_john.find_element("xpath",'//h3[contains(text(),"Global Bias")]')
        # print("Final " + str(global_bias.text))
        print('Success! :-)')  
        
    except NoSuchElementException:
        print('Failure! :-(')
    finally:
        # Clean up.
        driver_john.quit()
        # driver_paul.quit()
        