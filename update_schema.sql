-- Add Reorder Level to Products
ALTER TABLE products ADD COLUMN reorder_level INTEGER DEFAULT 10;

-- Add Batch, Expiry, Location to GRN
ALTER TABLE grn ADD COLUMN batch_no VARCHAR(50);
ALTER TABLE grn ADD COLUMN expiry_date DATE;
ALTER TABLE grn ADD COLUMN location VARCHAR(100);

-- Add Batch, Expiry, Location to Stock Ledger
ALTER TABLE stock_ledger ADD COLUMN batch_no VARCHAR(50);
ALTER TABLE stock_ledger ADD COLUMN expiry_date DATE;
ALTER TABLE stock_ledger ADD COLUMN location VARCHAR(100);
