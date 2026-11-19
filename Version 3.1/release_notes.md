# Changelog

# Changes from Version 3.0
------------------------
* "Verification Details" renamed to "Account Verification".
* Phone numbers are validated with a retry loop and saved in one format.
* Super Admin role expanded (admin accounts, system dashboard, changelogs).
* Admin accounts are created only by the Super Admin (fixed default accounts
  are seeded on first run).
* Customers and Store Owners are logged in automatically after registering.
* Products now have a unit (kg, g, L, mL, piece, pack, ...). The price is set
  PER UNIT and the quantity is the available stock in that unit.
* Decimal quantities are allowed only for weight and volume units.
* Store Owners can edit their own products.
* Changelog system (changelogs.json) records important activities.
* Passwords are hashed (legacy plain-text passwords are upgraded at login).
* Corrupted JSON files are backed up before being recreated.
* Clearer, more detailed messages for every output.


## Version 3.1 — 2026-11-02
- Added a system changelog for recording user activity.
- Added product units and support for decimal quantities.
- Improved account verification and phone-number validation.

# Version 3.1 - Release Date: November 2, 2026
- Added Features
- Added a system dashboard for viewing system statistics.
- Added Admin account management for the Super Admin.
- Added product editing for Store Owners.
- Added product removal for Admins.
- Added product units such as kg, g, L, mL, piece, pack, and bottle.
- Added decimal quantity support for weight and volume units.
- Added Store Owner application resubmission.
- Added product search filters for area, product name, and category.
- Added Store Pickup and Same-Day Express as fulfillment options.

# Improvements
- Expanded Super Admin permissions to include Admin management, system monitoring, and changelog viewing.
- Renamed "Verification Details" to "Account Verification".
- Improved phone number validation with retry prompts and consistent formatting.
- Customers and Store Owners are now logged in automatically after registration.
- Improved product quantity handling and validation.
- Improved purchase request validation and stock checking during confirmation.
- Improved store verification by checking required documents before approval.
- Added support for upgrading legacy plain text passwords after successful login.
- Improved system messages to make outputs clearer and more informative.

# Security and Data Handling
- Added password hashing using PBKDF2 with SHA256.
- Added account activation checks during login.
- Added automatic backups of corrupted JSON files before restoring default data.
- Added default unit handling for older product records without a unit.

# Notes

* Product prices are stored per unit.
* Product stock is not reserved when a customer submits a purchase request. Stock is deducted only after the Store Owner  confirms the request.
*  Same-Day Express is arranged directly with the Store Owner. The system does not provide delivery tracking.