# Product Admin Inlines Guide

## Overview

When creating or editing a product in Django admin, you'll see several inline sections at the **bottom of the form** (below all fieldsets). These inlines allow you to add:

1. **Size Options** - Product sizes (S, M, L, XL, etc.)
2. **Color Options** - Product colors with hex codes
3. **SKUs** - Stock keeping units (combinations of size + color with pricing and stock)
4. **Gallery Images** - Additional product images
5. **Features** - Product features/specifications

## Where to Find Inlines

**Important:** Inlines appear **below all fieldsets** in the Django admin form. You need to **scroll down** past:

- Basic Information
- Main Image
- Category Structure
- Pricing
- Product Details
- Status
- Statistics (collapsed)
- Timestamps (collapsed)

After all these sections, you'll see the inline sections.

## Inline Sections

### 1. Size Options

- **Purpose:** Define available sizes for the product
- **Fields:**
  - Name (e.g., "S", "M", "L", "XL")
  - Sort order
  - Is active
- **Note:** Add sizes first, as colors and SKUs depend on them

### 2. Color Options

- **Purpose:** Define available colors for the product
- **Fields:**
  - Size (links to size options you created above)
  - Name (e.g., "Red", "Blue")
  - Hex code (color code like "#FF0000")
  - Is active
- **Note:** Requires size options to be added first

### 3. SKUs (Stock Keeping Units)

- **Purpose:** Create product variants with specific size + color combinations
- **Fields:**
  - SKU code (auto-generated, readonly)
  - Size option (from size options above)
  - Color option (from color options above)
  - Price (can override product base price)
  - Original price
  - Currency
  - Stock (quantity available)
  - Variant image (specific image for this variant)
  - Is active
- **Note:** Requires both size and color options to be added first

### 4. Gallery Images

- **Purpose:** Add multiple product images for gallery
- **Fields:**
  - Image (upload file)
  - Alt text (for accessibility)
  - Sort order (display order)
- **Note:** This is separate from the main product image (in "Main Image" fieldset)

### 5. Features

- **Purpose:** Add product features/specifications
- **Fields:**
  - Feature text (description of feature)
  - Sort order (display order)

## Workflow for Creating a Product

1. **Fill in basic product information:**

   - Name, description, store, brand
   - Upload main image
   - Select category structure
   - Set pricing
   - Set product details

2. **Scroll down to inlines section**

3. **Add Size Options:**

   - Click "Add another Size Option"
   - Enter size name (e.g., "S")
   - Set sort order
   - Mark as active
   - Repeat for all sizes

4. **Add Color Options:**

   - Click "Add another Color Option"
   - Select size (from sizes you just added)
   - Enter color name
   - Enter hex code
   - Mark as active
   - Repeat for all colors

5. **Add SKUs:**

   - Click "Add another SKU"
   - Select size option
   - Select color option
   - Set price (or leave to use product base price)
   - Set stock quantity
   - Upload variant image (optional)
   - Mark as active
   - Repeat for all size/color combinations

6. **Add Gallery Images:**

   - Click "Add another Gallery Image"
   - Upload image
   - Add alt text
   - Set sort order
   - Repeat for all gallery images

7. **Add Features:**

   - Click "Add another Feature"
   - Enter feature text
   - Set sort order
   - Repeat for all features

8. **Click "Save"** at the bottom

## Troubleshooting

### Inlines Not Visible

1. **Scroll down:** Inlines appear at the bottom of the form, after all fieldsets
2. **Check browser console:** Look for JavaScript errors
3. **Try refreshing:** Hard refresh (Ctrl+Shift+R or Cmd+Shift+R)
4. **Check permissions:** Ensure you have staff access

### Can't Add SKUs

- **Problem:** Size/color dropdowns are empty
- **Solution:** Add size options first, then color options, then SKUs
- **Note:** When creating a new product, you may need to save once, then edit to add SKUs (or add them in the correct order)

### Foreign Key Errors

- **Problem:** "Size option" or "Color option" not found
- **Solution:** Ensure you've added size and color options before creating SKUs
- **Workaround:** Save the product first with sizes/colors, then edit to add SKUs

## Tips

1. **Order matters:** Add sizes → colors → SKUs in that order
2. **Save frequently:** Save the product after adding sizes/colors, then add SKUs
3. **Use sort order:** Set sort orders to control display sequence
4. **Main image vs gallery:** Main image is in the "Main Image" fieldset, gallery images are in the inline section
5. **SKU codes:** Auto-generated, don't need to set manually

## Quick Reference

- **Main Image:** In "Main Image" fieldset (single image)
- **Gallery Images:** In "Gallery Images" inline (multiple images)
- **Sizes:** In "Size Options" inline
- **Colors:** In "Color Options" inline (requires sizes)
- **SKUs:** In "SKUs" inline (requires sizes and colors)
- **Features:** In "Features" inline
