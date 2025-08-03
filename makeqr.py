import qrcode

# Prompt for user id and deck name
user_id = input("Enter the user id: ").strip()
deck_name = input("Enter the deck name: ").strip()

# (Optional) Replace spaces with dashes or underscores if you want to keep the URL clean
user_id_clean = user_id.replace(" ", "-")
deck_name_clean = deck_name.replace(" ", "-")

# Construct the URL
url = f"https://www.themeqr.com/go.html/?id={user_id_clean}"

# Generate and save the QR code
img = qrcode.make(url)
img.save(f"{user_id_clean}_{deck_name_clean}_qr.png") 

print(f"QR code generated for {url} and saved as {deck_name_clean}_qr.png")
