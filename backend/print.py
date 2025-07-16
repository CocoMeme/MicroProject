from PIL import Image, ImageDraw, ImageFont
import qrcode
import json
from datetime import datetime
import os
import pygame  # <-- added

class ReceiptPrinter:
    def __init__(self):
        self.printer_device = '/dev/usb/lp0'
        try:
            self.font_regular = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
            self.font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 18)
            self.font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
        except:
            self.font_regular = ImageFont.load_default()
            self.font_title = ImageFont.load_default()
            self.font_large = ImageFont.load_default()

    def create_receipt(self, order_data):
        try:
            qr = qrcode.QRCode(version=1, box_size=16, border=4)
            qr.add_data(str(order_data['orderNumber']))
            qr.make(fit=True)
            qr_img = qr.make_image(fill_color="black", back_color="white").convert('RGB')

            qr_width = 400
            qr_height = int(qr_width * qr_img.height / qr_img.width)
            qr_img = qr_img.resize((qr_width, qr_height))

            text_height_regular = 25
            text_height_large = 35
            spacing = 15

            header_height = text_height_regular * 5  # Updated from 4 to 5 for contact number
            product_section_height = text_height_large * 2
            footer_height = text_height_regular  # Updated back to original for just date

            total_height = (
                spacing + header_height + spacing +
                product_section_height + spacing +
                footer_height + spacing + qr_height + spacing
            )

            receipt = Image.new('RGB', (384, total_height), 'white')
            draw = ImageDraw.Draw(receipt)
            y = spacing

            draw.text((10, y), f"Order-id: {order_data['orderNumber']}", font=self.font_title, fill='black')
            y += text_height_regular
            draw.text((10, y), f"Customer: {order_data['customerName']}", font=self.font_regular, fill='black')
            y += text_height_regular
            draw.text((10, y), f"Email: {order_data['email']}", font=self.font_regular, fill='black')
            y += text_height_regular
            draw.text((10, y), f"Contact: {order_data.get('contactNumber', 'N/A')}", font=self.font_regular, fill='black')
            y += text_height_regular
            draw.text((10, y), f"Address: {order_data['address']}", font=self.font_regular, fill='black')
            y += text_height_regular + spacing

            draw.text((10, y), f"Product: {order_data['productName']}", font=self.font_large, fill='black')
            y += text_height_large
            draw.text((10, y), f"Amount: {order_data['amount']}", font=self.font_large, fill='black')
            y += text_height_large + spacing

            draw.text((10, y), f"Date: {order_data['date']}", font=self.font_regular, fill='black')
            y += text_height_regular + spacing

            draw.line([(10, y), (374, y)], fill='black', width=1)
            y += spacing

            receipt.paste(qr_img, (0, y))
            return receipt

        except Exception as e:
            print(f"Error creating receipt: {e}")
            return None

    def print_receipt(self, receipt):
        # ✅ Play sound after successful print
        pygame.mixer.init()
        sound = pygame.mixer.Sound("/home/test/Desktop/sound/success.mp3")
        sound.play()

        try:
            receipt = receipt.convert('1')

            with open(self.printer_device, 'wb') as p:
                p.write(b'\x1b\x40')  # ESC @
                p.write(b'\x1b\x61\x01')  # Center alignment

                width_bytes = (receipt.width + 7) // 8
                p.write(b'\x1d\x76\x30\x00')
                p.write(bytes([width_bytes & 0xff, width_bytes >> 8]))
                p.write(bytes([receipt.height & 0xff, receipt.height >> 8]))

                pixels = receipt.load()
                for y in range(receipt.height):
                    for x in range(0, receipt.width, 8):
                        byte = 0
                        for bit in range(min(8, receipt.width - x)):
                            if pixels[x + bit, y] == 0:
                                byte |= (1 << (7 - bit))
                        p.write(bytes([byte]))

                p.write(b'\n\n\n\n')
                p.write(b'\x1d\x56\x41\x03')  # Cut

            return True, "Print successful"

        except Exception as e:
            print(f"Error printing: {e}")
            try:
                receipt.save('last_failed_print.png')
                return False, f"Print failed (saved as last_failed_print.png): {str(e)}"
            except:
                return False, f"Print failed: {str(e)}"

    def check_printer(self):
        return os.path.exists(self.printer_device)
