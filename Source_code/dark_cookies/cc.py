# From the sfl module import the required functions
from dark_cookies.sfl import save_cookies
from time import sleep
import logging


# Class which handles the additional cookie captures which require a fresh webpage to be loaded.
class Cookie_Capture:
    def __init__(self, conf):
        # The WebDriver instance
        self.driver = conf.driver
        self.conf = conf
        # The domain of the website
        self.domain = conf.domain
        # The option to make the program fully automatic
        self.OPT_AUTO = conf.options.OPT_AUTO
        # The option to enable Cookie Rejector
        self.OPT_CR = conf.options.OPT_CR
        self.resultsDB = conf.resultsDB
        
        
    def additional_captures(self):
        """ Main function which triggers the other captures functions as required.
        """
        # Capture cookies after clicking the opt-in button.
        self.opt_in_button_capture()
        # Capture cookies after clicking the close button.
        self.close_button_capture()
        # Capture cookies after clicking the opt-out button.
        self.opt_out_button_capture()
        
    
    def close_button_capture(self):
        """ Function which is used to click the close button on the cookie dialog and record the number of cookies after.
        """
        # Call the button function to click close buttons.
        self.button_type_click("close option")
        
        
    def opt_in_button_capture(self):
        """ Function which is used to click the opt-in button on the cookie dialog and record the number of cookies after.
        """
        # Call the opt-in function to click opt-in buttons.
        self.button_type_click("opt-in option")
        
    def opt_out_button_capture(self):
        """ Function which is used to click the opt-out button on the cookie dialog and record the number of cookies after.
        """
        # Call the opt-in function to click opt-out buttons.
        if not self.OPT_CR:
            self.button_type_click("opt-out option")
        
        
    def button_type_click(self, button_type):
        """
        Click a given button type and save cookies after that state.
        Uses a TEMP webdriver and restores the original CDA driver afterward.
        """
        # Retrieve clickables tagged on the dialog
        if self.OPT_AUTO:
            clickables = self.resultsDB.clickables.select_clickableNum_autoType(self.domain)
        else:
            clickables = self.resultsDB.clickables.select_clickableNum_type(self.domain)
        clickables = {c[0]: c[1] for c in clickables}
        clickables_types = set(clickables.values())

        if button_type not in clickables_types:
            logging.info("No '%s' clickable recorded for %s.", button_type, self.domain)
            return

        logging.info("Capturing '%s' cookies...", button_type)

        # Keep original Stage-4 driver
        original_driver = self.conf.driver

        # Spin up a TEMP driver for this capture
        self.conf.create_webdriver()
        temp_driver = self.conf.driver
        if temp_driver is None:
            logging.error("Failed to create temp driver for '%s' capture.", button_type)
            self.conf.driver = original_driver
            return

        try:
            # Match the exact recorded button
            button_num = next((c for c, t in clickables.items() if t == button_type), None)
            if button_num is None:
                logging.info("No button_num for '%s'.", button_type)
                return

            button_html = self.resultsDB.clickables.select_rawHTML(self.domain, button_num)
            button_text = self.resultsDB.clickables.select_text(self.domain, button_num)

            if self.OPT_AUTO:
                selectors = self.resultsDB.clickables.select_CSSSelector_where_autoType(self.domain, button_type)
            else:
                selectors = self.resultsDB.clickables.select_CSSSelector_where_type(self.domain, button_type)

            for (css_sel,) in selectors:
                try:
                    buttons = self.conf.driver.find_elements_by_css_selector(css_sel)
                except Exception:
                    continue
                for button in buttons:
                    try:
                        html = button.get_attribute('outerHTML')
                        text = button.text
                        if html == button_html or text == button_text:
                            try:
                                button.click()
                                sleep(30)  # keep your original timing
                                save_cookies(self.conf.driver, self.domain, self.resultsDB, button_type)
                                raise StopIteration  # break out of both loops
                            except Exception:
                                logging.debug("Error: Failed to click element.")
                    except Exception:
                        pass
        except StopIteration:
            pass
        except Exception as e:
            logging.debug("Error: Failed to %s (%s)", button_type, e)
        finally:
            # Close ONLY the temp driver we created and restore the original
            try:
                if self.conf.driver is temp_driver and self.conf.driver is not None:
                    self.conf.close_webdriver()
            finally:
                self.conf.driver = original_driver