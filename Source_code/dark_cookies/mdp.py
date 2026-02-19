# Import the required Interfaces from the User Input Interface module.
from dark_cookies.uii import Checkbox_Input
import logging


class Manual_Dark_Patterns():
    def __init__(self, conf):
        # The WebDriver instance
        self.driver = conf.driver
        # The domain of the website
        self.domain = conf.domain
        # Class attributes for the required configuartion options
        self.OPT_SAVE_COOKIES = conf.options.OPT_SAVE_COOKIES
        self.OPT_CR = conf.options.OPT_CR
        self.resultsDB = conf.resultsDB
        
        
    def find_dps(self):
        """ Function to allow the user to input any other DPs them and add them to the database.
        """
        logging.debug("Manually Adding DPs for '"+str(self.domain)+"'...")
        
        # Dark pattern descriptions
        dark_patterns_desc = {
                         "DP20" : "Poorly Labelled preference sliders to the extent that their purpose is ambiguous.",
                         "DP21" : "In the context of the Cookie Dialog text the standard meaning of the Opt-in and Opt-out buttons is inverted.",
                         "DP22" : "Opt-out button is named in such a way to guilt them for selecting it."
                         }

        # Define the intial values of the dark patterns (will all be False)
        dark_patterns = {d:False for d in dark_patterns_desc}
        
        clickables = self.resultsDB.clickables.select_clickableNum_type(self.domain)
        clickables = {c[0]:c[1] for c in clickables}
        clickables_types = set(clickables.values())
        
       
        # Save each dark pattern to the database
        for dp in dark_patterns:
           self.resultsDB.dark_patterns.insert_into(self.domain, dp, "unconfirmed", "unconfirmed")
        
        # Prompt the user to validate the auto DPs
        app = Checkbox_Input(input_values=dark_patterns, input_descriptions=dark_patterns_desc, description="Check all the Manual Dark Patterns and then click confirm.", window_name="MDP")
          # Save data and directly trigger the confirm button
        logging.debug("Automatically clicking the Confirm button.")
        confirm_button = None  # Directly invoke the Confirm button
        for widget in app.winfo_children():
            if "Confirm" in widget.cget("text"):
                confirm_button = widget
                break
        if confirm_button:
            confirm_button.invoke() # Directly invoke the Confirm button
        
        # Update the detected patterns in the database
        for dp, value in dark_patterns.items():
            self.resultsDB.dark_patterns.update_value(self.domain, dp, str(app.result[dp].get()))

        logging.info("All detected Dark Patterns have been auto-confirmed.")

        # Function to close the window after 5 seconds
        def close_window():
           app.master.quit()  # This will close the tkinter window

        # Wait for 5 seconds and then close the window
        app.after(5000, close_window)  # 5000 ms = 5 seconds

        # Run the tkinter mainloop to keep the window open for interaction
        app.mainloop()  # Keeps the window open for 5 seconds before closing