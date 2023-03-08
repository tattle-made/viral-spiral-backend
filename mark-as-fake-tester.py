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




global buttons
buttons = ["paul", "john", "george", "ringo"]
options = webdriver.ChromeOptions()


global new_player




def new_player(room_name, player_name,encyclopedia_activated):
    
    

    
    
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
           

            
            

            driver_player_name.refresh()
            sleep(5)           
            player_card_text = driver_player_name.find_element("xpath",'//div[contains(@class,"card-text")]')
            sleep(1) 
                
            
            player_choice_button = driver_player_name.find_element("xpath",'//button[contains(text(),"Mark as fake")]')

            
            sleep(2)
            
            
            print("the card text is: " + str(player_card_text.text))
            
            
            
            player_choice_button.click()
            sleep(2)
            
            
            
            print(str(player_name) + " Successfully Used Mark as Fake")
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

    encyclopedia_activated = Value('i', 0)
    

    
    print("Testing the special power: Mark as Fake")
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
        p_paul = multiprocessing.Process(target = new_player, args = [room_name,"paul",encyclopedia_activated])
        p_george = multiprocessing.Process(target = new_player, args = [room_name,"george",encyclopedia_activated])
        p_ringo = multiprocessing.Process(target = new_player, args = [room_name,"ringo",encyclopedia_activated]) 
        p_paul.start()
        p_george.start()
        p_ringo.start()
        
        print('parallel function executing')
        while True:
            
                
            try:
                # print(viral_spiral_activated.value)
                driver_john.refresh()
                sleep(5)           
                player_card_text = driver_john.find_element("xpath",'//div[contains(@class,"card-text")]')
                sleep(1) 
                    
                
                player_choice_button = driver_john.find_element("xpath",'//button[contains(text(),"Mark as fake")]')

                
                sleep(2)
                
                
                print("the card text is: " + str(player_card_text.text))
                
                
                
                player_choice_button.click()
                sleep(2)
                
                
                
                print("John Successfully Used Mark as Fake")
                sleep(2)
                

                

                sleep(30)
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