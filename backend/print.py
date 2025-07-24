from PIL import Image, ImageDraw, ImageFont
import qrcode
import json
from datetime import datetime
import os
import pygame
import threading
import time
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ReceiptPrinter:
    def __init__(self):
        self.printer_device = '/dev/usb/lp0'
        # Initialize pygame mixer once
        self._init_pygame()
        self._init_fonts()
        # Add thread lock for printer access
        self.printer_lock = threading.Lock()
        
    def _init_pygame(self):
        """Initialize pygame mixer safely"""
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            logger.info("Pygame mixer initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize pygame mixer: {e}")
            
    def _init_fonts(self):
        """Initialize fonts with fallbacks"""
        try:
            self.font_regular = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
            self.font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 18)
            self.font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
            logger.info("Custom fonts loaded successfully")
        except Exception as e:
            logger.warning(f"Failed to load custom fonts, using default: {e}")
            self.font_regular = ImageFont.load_default()
            self.font_title = ImageFont.load_default()
            self.font_large = ImageFont.load_default()

    def create_receipt(self, order_data):
        """Create receipt image in receipt style format without QR code"""
        try:
            # Validate input data
            if not order_data or not isinstance(order_data, dict):
                raise ValueError("Invalid order data provided")
                
            # Check required fields
            required_fields = ['orderNumber', 'customerName', 'productName', 'amount', 'date']
            missing_fields = [field for field in required_fields if not order_data.get(field)]
            if missing_fields:
                raise ValueError(f"Missing required fields: {missing_fields}")

            # Calculate layout dimensions for receipt style
            text_height_regular = 25
            text_height_large = 35
            text_height_title = 30
            spacing = 15
            line_spacing = 5

            # Calculate total height needed for receipt-style layout
            header_section = text_height_title + spacing  # Store/business header
            separator_line = line_spacing + spacing
            order_section = text_height_regular * 2 + spacing  # Order ID and Date
            customer_section = text_height_regular * 3  # Customer, Contact, Address
            # Add extra height if email exists
            if order_data.get('email') and order_data['email'].strip():
                customer_section += text_height_regular
            product_section = text_height_large * 2 + spacing  # Product and Amount
            footer_section = text_height_regular * 2 + spacing  # Thank you message

            total_height = (
                spacing + header_section + separator_line + order_section + 
                separator_line + customer_section + separator_line + 
                product_section + separator_line + footer_section + spacing
            )

            # Create receipt image
            receipt = Image.new('RGB', (384, total_height), 'white')
            draw = ImageDraw.Draw(receipt)
            y = spacing

            # Store/Business Header (centered)
            business_name = "ORDER RECEIPT"
            bbox = draw.textbbox((0, 0), business_name, font=self.font_large)
            text_width = bbox[2] - bbox[0]
            x_center = (384 - text_width) // 2
            draw.text((x_center, y), business_name, font=self.font_large, fill='black')
            y += text_height_title + spacing

            # First separator line
            draw.line([(10, y), (374, y)], fill='black', width=1)
            y += line_spacing + spacing

            # Order Information Section
            draw.text((10, y), f"Order ID: {str(order_data['orderNumber'])}", font=self.font_title, fill='black')
            y += text_height_regular
            draw.text((10, y), f"Date: {str(order_data['date'])}", font=self.font_regular, fill='black')
            y += text_height_regular + spacing

            # Second separator line
            draw.line([(10, y), (374, y)], fill='black', width=1)
            y += line_spacing + spacing

            # Customer Information Section
            draw.text((10, y), f"Customer: {str(order_data['customerName'])}", font=self.font_regular, fill='black')
            y += text_height_regular
            
            # Only show email if it exists and is not empty
            if order_data.get('email') and order_data['email'].strip():
                draw.text((10, y), f"Email: {str(order_data['email'])}", font=self.font_regular, fill='black')
                y += text_height_regular
                
            draw.text((10, y), f"Contact: {str(order_data.get('contactNumber', 'N/A'))}", font=self.font_regular, fill='black')
            y += text_height_regular
            draw.text((10, y), f"Address: {str(order_data.get('address', 'N/A'))}", font=self.font_regular, fill='black')
            y += text_height_regular + spacing

            # Third separator line
            draw.line([(10, y), (374, y)], fill='black', width=1)
            y += line_spacing + spacing

            # Product and Amount Section
            draw.text((10, y), f"Product: {str(order_data['productName'])}", font=self.font_large, fill='black')
            y += text_height_large
            
            # Format amount with currency symbol
            amount_str = f"₱ {str(order_data['amount'])}"
            draw.text((10, y), f"Amount: {amount_str}", font=self.font_large, fill='black')
            y += text_height_large + spacing

            # Final separator line
            draw.line([(10, y), (374, y)], fill='black', width=1)
            y += line_spacing + spacing

            # Footer Section (centered)
            thank_you_msg = "Thank you for your order!"
            bbox = draw.textbbox((0, 0), thank_you_msg, font=self.font_regular)
            text_width = bbox[2] - bbox[0]
            x_center = (384 - text_width) // 2
            draw.text((x_center, y), thank_you_msg, font=self.font_regular, fill='black')
            y += text_height_regular
            
            # Print date/time
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            printed_msg = f"Printed: {current_time}"
            bbox = draw.textbbox((0, 0), printed_msg, font=self.font_regular)
            text_width = bbox[2] - bbox[0]
            x_center = (384 - text_width) // 2
            draw.text((x_center, y), printed_msg, font=self.font_regular, fill='black')
            
            logger.info(f"Receipt created successfully for order {order_data['orderNumber']}")
            return receipt

        except Exception as e:
            logger.error(f"Error creating receipt: {e}")
            return None

    def _play_success_sound(self):
        """Play success sound in a separate thread to avoid blocking"""
        def play_sound():
            try:
                if pygame.mixer.get_init():
                    sound_path = "/home/test/Desktop/sound/success.mp3"
                    if os.path.exists(sound_path):
                        sound = pygame.mixer.Sound(sound_path)
                        sound.play()
                        logger.info("Success sound played")
                    else:
                        logger.warning(f"Sound file not found: {sound_path}")
                else:
                    logger.warning("Pygame mixer not initialized")
            except Exception as e:
                logger.error(f"Failed to play success sound: {e}")
        
        # Play sound in background thread to avoid blocking
        threading.Thread(target=play_sound, daemon=True).start()

    def print_receipt(self, receipt):
        """Print receipt with thread safety and better error handling"""
        if not receipt:
            return False, "No receipt to print"
            
        # Use thread lock to prevent concurrent printer access
        with self.printer_lock:
            try:
                # Check printer availability
                if not self.check_printer():
                    return False, "Printer device not available"

                # Convert to 1-bit image for thermal printer
                receipt_bw = receipt.convert('1')
                
                # Save backup copy before printing
                backup_path = f"/tmp/receipt_backup_{int(time.time())}.png"
                try:
                    receipt.save(backup_path)
                    logger.info(f"Receipt backup saved to {backup_path}")
                except Exception as e:
                    logger.warning(f"Failed to save backup: {e}")

                # Print with timeout and retries
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        with open(self.printer_device, 'wb') as p:
                            # ESC/POS commands
                            p.write(b'\x1b\x40')  # ESC @ - Initialize printer
                            p.write(b'\x1b\x61\x01')  # Center alignment

                            # Calculate image dimensions
                            width_bytes = (receipt_bw.width + 7) // 8
                            p.write(b'\x1d\x76\x30\x00')  # Print raster bit image
                            p.write(bytes([width_bytes & 0xff, width_bytes >> 8]))
                            p.write(bytes([receipt_bw.height & 0xff, receipt_bw.height >> 8]))

                            # Send image data
                            pixels = receipt_bw.load()
                            for y in range(receipt_bw.height):
                                for x in range(0, receipt_bw.width, 8):
                                    byte = 0
                                    for bit in range(min(8, receipt_bw.width - x)):
                                        if pixels[x + bit, y] == 0:  # Black pixel
                                            byte |= (1 << (7 - bit))
                                    p.write(bytes([byte]))

                            # Feed paper and cut
                            p.write(b'\n\n\n\n')
                            p.write(b'\x1d\x56\x41\x03')  # Cut paper
                            p.flush()  # Ensure all data is sent

                        # If we get here, printing succeeded
                        logger.info("Receipt printed successfully")
                        self._play_success_sound()
                        return True, "Print successful"

                    except (IOError, OSError) as e:
                        logger.warning(f"Print attempt {attempt + 1} failed: {e}")
                        if attempt == max_retries - 1:
                            # Save failed print for debugging
                            try:
                                receipt.save('last_failed_print.png')
                                logger.info("Failed print saved as last_failed_print.png")
                            except Exception as save_e:
                                logger.error(f"Failed to save failed print: {save_e}")
                            return False, f"Print failed after {max_retries} attempts: {str(e)}"
                        else:
                            time.sleep(1)  # Wait before retry

            except Exception as e:
                logger.error(f"Unexpected error during printing: {e}")
                return False, f"Print failed: {str(e)}"

    def create_qr_only(self, order_number):
        """Create QR code image only without any receipt details"""
        try:
            if not order_number:
                raise ValueError("Order number is required for QR code generation")

            # Create QR code
            qr = qrcode.QRCode(version=1, box_size=16, border=4)
            qr.add_data(str(order_number))
            qr.make(fit=True)
            qr_img = qr.make_image(fill_color="black", back_color="white").convert('RGB')
            
            # Resize QR code to fit thermal printer width (384px)
            qr_width = 384
            qr_height = int(qr_width * qr_img.height / qr_img.width)
            qr_img = qr_img.resize((qr_width, qr_height))
            
            logger.info(f"QR code created successfully for order {order_number}")
            return qr_img

        except Exception as e:
            logger.error(f"Error creating QR code: {e}")
            return None

    def print_qr_only(self, order_number):
        """Print only QR code without receipt details"""
        try:
            qr_image = self.create_qr_only(order_number)
            if not qr_image:
                return False, "Failed to create QR code"
            
            success, message = self.print_receipt(qr_image)
            if success:
                logger.info(f"QR code printed successfully for order {order_number}")
            return success, message
            
        except Exception as e:
            logger.error(f"Error printing QR code: {e}")
            return False, f"Print QR failed: {str(e)}"

    def check_printer(self):
        """Check if printer device is available"""
        try:
            is_available = os.path.exists(self.printer_device)
            logger.debug(f"Printer check: {self.printer_device} - {'Available' if is_available else 'Not available'}")
            return is_available
        except Exception as e:
            logger.error(f"Error checking printer: {e}")
            return False
