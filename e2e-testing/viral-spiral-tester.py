from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager # use pip install webdriver_manager
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import StaleElementReferenceException
from time import sleep
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.by import By
import multiprocessing
from multiprocessing import Value, Process
import random

global num_of_players
num_of_players = 4



global buttons
buttons = ["paul", "john", "george", "ringo"]
options = webdriver.ChromeOptions()


global main_card_text
global new_player
global viral_spiral_activator



def new_player(room_name, player_name, viral_spiral_activated, players_receiving_viral_spiral):
    
    

    num_of_players = 4
    
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
            # print(viral_spiral_activated.value)

            if(viral_spiral_activated.value == 1):
                driver_player_name.refresh()
                    
                sleep(10)
                print("Checking if " + str(player_name) +" received card")
                recieved_card = driver_player_name.find_element("xpath",'//div[contains(@class,"card-text")]')
                sleep(2)
                print("The text of the card received by " + str(player_name) + " is: " + str(recieved_card.text))
                players_receiving_viral_spiral.value = players_receiving_viral_spiral.value + 1
                sleep(2)
                break
                
            
            elif(viral_spiral_activated.value == 0):
                driver_player_name.refresh()
                sleep(5)           
                player_card_text = driver_player_name.find_element("xpath",'//div[contains(@class,"card-text")]')
                sleep(1) 
                    
                
                player_choice_button = driver_player_name.find_element("xpath",'//button[contains(text(),"Viral Spiral")]')
                
                sleep(2)
                
                
                print("the card text is: " + str(player_card_text.text))
                
                
                
                player_choice_button.click()
                sleep(2)
                
                for button in buttons:
                    if button != player_name:
                        player_check_box = driver_player_name.find_element("xpath",'//label[contains(@label,"{}")]'.format(button))
                        # sleep(2)
                        player_check_box.click()
                        sleep(1)
                send_button_player = driver_player_name.find_element("xpath",'//button[contains(text(),"Send")]')
                send_button_player.click()
                viral_spiral_activated.value = 1
                print(str(player_name) + " initiated Viral Spiral")
                sleep(2)

                while(players_receiving_viral_spiral.value != (num_of_players - 1)):
                    continue

                print(str(player_name) + " successfully used Viral Spiral")
                sleep(2)
                break

            


        except NoSuchElementException:
            sleep(2)
            
            # print(str(player_name) + " be waiting")
            continue
        except StaleElementReferenceException:
            sleep(2)
            # print(str(player_name) + " be waiting")
            continue
    
    sleep(2)
    driver_player_name.quit()

if __name__ == '__main__' :

    viral_spiral_activated = Value('i', 0)
    players_receiving_viral_spiral = Value('i', 0)

    
    print("Testing the special power: Viral Spiral")
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
        player_count.send_keys(str(num_of_players))

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
        p_paul = multiprocessing.Process(target = new_player, args = [room_name,"paul",viral_spiral_activated, players_receiving_viral_spiral])
        p_george = multiprocessing.Process(target = new_player, args = [room_name,"george", viral_spiral_activated, players_receiving_viral_spiral])
        p_ringo = multiprocessing.Process(target = new_player, args = [room_name,"ringo", viral_spiral_activated, players_receiving_viral_spiral]) 
        p_paul.start()
        p_george.start()
        p_ringo.start()
        
        print('parallel function executing')
        while True:
            
                
            try:
                # print(viral_spiral_activated.value)
                if(viral_spiral_activated.value == 1):
                   
                    driver_john.refresh()
                    
                    sleep(10)
                    print("Checking if john received card")
                    recieved_card = driver_john.find_element("xpath",'//div[contains(@class,"card-text")]')
                    sleep(2)
                    print("The text of the card received by john is: " + str(recieved_card.text))
                    players_receiving_viral_spiral.value = players_receiving_viral_spiral.value + 1
                    sleep(15)
                    break
                    
                
            
                elif(viral_spiral_activated.value == 0):
                    driver_john.refresh()
                    sleep(5)           
                    player_card_text = driver_john.find_element("xpath",'//div[contains(@class,"card-text")]')
                    sleep(1) 
                        
                    
                    player_choice_button = driver_john.find_element("xpath",'//button[contains(text(),"Viral Spiral")]')
                    
                    sleep(2)
                    
                    
                    print("the card text is: " + str(player_card_text.text))
                    main_card_text = player_card_text.text
                    viral_spiral_activator = "john"
                    
                    player_choice_button.click()
                    sleep(2)
                    
                    for button in buttons:
                        if button != "john":
                            player_check_box = driver_john.find_element("xpath",'//label[contains(@label,"{}")]'.format(button))
                            # sleep(2)
                            player_check_box.click()
                            sleep(1)
                    send_button_player = driver_john.find_element("xpath",'//button[contains(text(),"Send")]')
                    send_button_player.click()
                    viral_spiral_activated.value = 1
                    print("john initiated Viral Spiral")
                    sleep(2)

                    while(players_receiving_viral_spiral.value != (num_of_players - 1)):
                        continue

                    print("john successfully used Viral Spiral")
                    
                    sleep(15)
                    break
            except NoSuchElementException:
                sleep(2)
                
                # print("john be waiting")
                continue
            except StaleElementReferenceException:
                sleep(2)
                # print("john be waiting")
                continue
        
        
        
    except NoSuchElementException:
        print('Failure! :-(')
    finally:
        # Clean up.
        p_george.join()
        p_paul.join()
        p_ringo.join()
        driver_john.quit()
        
        