# Scripts

Rundowns of the scripts present in this folder

## xls_to_json

### A note about running the xls_to_json file:

Since the file reads an ods, you need to specify the path to the ods file as a system variable in the command to run the file itself. The example to this can be seen in the rundown below. Secondly the file would output the `cards.json` file in the same folder. Based on how the directory is structured, you will need to move this file to the `config_jsons/example1/` folder and replace the card.json there with the new data. This is recommeded since the data might be stale when a new card drawing logic is pushed

### Rundown:

Converts a given excel sheet into a JSON dump in a particular format which can then be used to populate the database.
The following line of code read the data and stores it into the `df` variable:
```
ods_path = sys.argv[1]
sheet_name = "Cards Master"
df = read_ods(ods_path, sheet_name)
```
Note that in order to run the script properly, you need to add the name of the excel sheet after the filename, for instance: `python xls_to_json.py example.ods`

Next, the script iterates through all the rows of the sheet using a for loop. The main function of interest inside the for loop is `use_iloc()`. Is essentially iterates through the row in sequential fashion by usint the `.iloc[]` function of pandas. The `.iloc[]` pandas function is useful to iterate through a set of rows or columns by providing integer index or locator (hence the name). The script sets the value of this locator in the `iloc` variable at the beginning of a new iteration of the for loop as 0. Next, whenever an element in the row needs to be referenced the syntax `row.iloc[use_iloc()]` is used. 

The `use_iloc()` function does three things: 
    - Store the current value of the `iloc` variable
    - Increment the value of the `iloc` variable by 1
    - Return the previously stored value of the `iloc` variable

Thus by using the syntax `row.iloc[use_iloc()]`, the current element in the row is referenced and it's value is stored inside a dict data structure (which uses the same formatting as JSON) pertaining to a card. At the same time the value of the `iloc` variable is increased in order for the same syntax to then reference the next element in the row. Thus, sequentially, one iteration of the for loop goes through the entire row, appending cards as and when all data is inserted into them. Firstly, the factual cards, then the Bias cards for colors followed finally by the topic cards (This is also the order in which each row of the data in "Cards Master" file is structured, which is the input file for the script). 

Note that since some cards have the `Fake` label entered whilst others do not, the function 

```
def is_valid_cell(text):
    return text and text.strip() and text.strip() != "null"
```

checks for the presence of a fake description. It returns a boolean, which would be false if a fake description for a card does not exist and the script returns a null list if the function returns false for a given card's data in the `Fake` label. 

The last block of the code saves the json data in a file named `cards_data.json`
