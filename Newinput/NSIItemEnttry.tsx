import React, { useState, CSSProperties } from 'react';

interface ItemDetails {
  item_id: string;
  description: string;
  quantity: number;
  value: number;
}

interface NSIItemFormData {
  trackingNumber: string;
  item_id: string;
  description: string;
  disposition: string;
  vendorId: string;
  quantity: number;
  value: number;
  location_id: string;
  created_date: string;
}

// Styles
const styles = {
  container: {
    maxWidth: '900px',
    margin: '0 auto',
    padding: '20px',
    backgroundColor: '#f9f9f9',
    borderRadius: '8px',
    boxShadow: '0 2px 4px rgba(0, 0, 0, 0.1)',
    fontFamily: 'inherit',
  } as CSSProperties,
  header: {
    textAlign: 'center' as const,
    marginBottom: '30px',
    borderBottom: '2px solid #007bff',
    paddingBottom: '20px',
  } as CSSProperties,
  headerH1: {
    margin: '0',
    fontSize: '28px',
    color: '#333',
    fontWeight: '600',
  } as CSSProperties,
  subtitle: {
    margin: '8px 0 0 0',
    fontSize: '14px',
    color: '#666',
    fontWeight: '400',
  } as CSSProperties,
  main: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '25px',
  } as CSSProperties,
  section: {
    backgroundColor: '#fff',
    padding: '20px',
    borderRadius: '6px',
    border: '1px solid #e0e0e0',
  } as CSSProperties,
  sectionTitle: {
    fontSize: '18px',
    fontWeight: '600',
    color: '#333',
    margin: '0 0 15px 0',
    paddingBottom: '10px',
    borderBottom: '1px solid #e0e0e0',
  } as CSSProperties,
  formGroup: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '8px',
    marginBottom: '15px',
  } as CSSProperties,
  formRow: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: '20px',
    marginBottom: '15px',
  } as CSSProperties,
  formLabel: {
    fontSize: '14px',
    fontWeight: '600',
    color: '#333',
    display: 'flex',
    alignItems: 'center',
    gap: '4px',
  } as CSSProperties,
  required: {
    color: '#dc3545',
    fontWeight: 'bold',
  } as CSSProperties,
  formInput: {
    padding: '10px 12px',
    border: '1px solid #ccc',
    borderRadius: '4px',
    fontSize: '14px',
    fontFamily: 'inherit',
    transition: 'border-color 0.3s ease, box-shadow 0.3s ease',
  } as CSSProperties,
  inputGroup: {
    display: 'flex',
    gap: '10px',
    alignItems: 'stretch',
  } as CSSProperties,
  trackingInput: {
    flex: 1,
    padding: '10px 12px',
    border: '1px solid #ccc',
    borderRadius: '4px',
    fontSize: '14px',
    fontFamily: 'inherit',
    transition: 'border-color 0.3s ease, box-shadow 0.3s ease',
  } as CSSProperties,
  detailsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
    gap: '15px',
    padding: '15px 0',
  } as CSSProperties,
  detailField: {
    padding: '10px',
    backgroundColor: '#f5f5f5',
    borderRadius: '4px',
    borderLeft: '4px solid #007bff',
  } as CSSProperties,
  detailLabel: {
    fontSize: '12px',
    fontWeight: '600',
    color: '#666',
    textTransform: 'uppercase' as const,
    display: 'block',
    marginBottom: '4px',
  } as CSSProperties,
  detailValue: {
    fontSize: '15px',
    color: '#333',
    fontWeight: '500',
  } as CSSProperties,
  button: {
    padding: '10px 20px',
    border: 'none',
    borderRadius: '4px',
    fontSize: '14px',
    fontWeight: '600',
    cursor: 'pointer',
    transition: 'all 0.3s ease',
    textTransform: 'uppercase' as const,
    letterSpacing: '0.5px',
  } as CSSProperties,
  btnPrimary: {
    backgroundColor: '#007bff',
    color: '#fff',
    whiteSpace: 'nowrap' as const,
    padding: '10px 25px',
  } as CSSProperties,
  btnSuccess: {
    backgroundColor: '#28a745',
    color: '#fff',
    flex: 1,
  } as CSSProperties,
  btnSecondary: {
    backgroundColor: '#6c757d',
    color: '#fff',
    flex: 1,
  } as CSSProperties,
  actionButtons: {
    display: 'flex',
    gap: '15px',
    justifyContent: 'center',
    paddingTop: '20px',
    borderTop: '2px solid #e0e0e0',
  } as CSSProperties,
  errorMessage: {
    padding: '12px 15px',
    backgroundColor: '#f8d7da',
    border: '1px solid #f5c6cb',
    borderRadius: '4px',
    color: '#721c24',
    fontSize: '14px',
    marginBottom: '15px',
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  } as CSSProperties,
  warningMessage: {
    padding: '12px 15px',
    backgroundColor: '#fff3cd',
    border: '1px solid #ffeeba',
    borderRadius: '4px',
    color: '#856404',
    fontSize: '14px',
    marginBottom: '15px',
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  } as CSSProperties,
  successMessage: {
    padding: '12px 15px',
    backgroundColor: '#d4edda',
    border: '1px solid #c3e6cb',
    borderRadius: '4px',
    color: '#155724',
    fontSize: '14px',
    marginBottom: '15px',
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  } as CSSProperties,
};

const NSIItemEntry: React.FC = () => {
  const [trackingNumber, setTrackingNumber] = useState('');
  const [itemDetails, setItemDetails] = useState<ItemDetails | null>(null);
  const [isScanned, setIsScanned] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [warningMessage, setWarningMessage] = useState('');
  const [scannedItems, setScannedItems] = useState<string[]>([]);
  const [formData, setFormData] = useState<NSIItemFormData>({
    trackingNumber: '',
    item_id: '',
    description: '',
    disposition: '',
    vendorId: '',
    quantity: 0,
    value: 0,
    location_id: '',
    created_date: new Date().toISOString(),
  });

  const handleTrackingNumberChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setTrackingNumber(e.target.value);
    setErrorMessage('');
    setWarningMessage('');
  };

  const handleScanClick = async () => {
    setErrorMessage('');
    setWarningMessage('');

    // Validate tracking number is not empty
    if (!trackingNumber.trim()) {
      setErrorMessage('Please enter a tracking number');
      return;
    }

    // Check for duplicate item already in worklist
    if (scannedItems.includes(trackingNumber)) {
      setWarningMessage('Item already in worklist');
      setTrackingNumber('');
      return;
    }

    try {
      // Simulate API call to fetch item from inventory table
      const fetchedItem = await fetchItemFromInventory(trackingNumber);

      if (fetchedItem) {
        // Item found - populate details
        setItemDetails(fetchedItem);
        setIsScanned(true);
        setFormData((prev) => ({
          ...prev,
          trackingNumber: trackingNumber,
          item_id: fetchedItem.item_id,
          description: fetchedItem.description,
          quantity: fetchedItem.quantity,
          value: fetchedItem.value,
        }));
      } else {
        // Item not found
        setErrorMessage('Invalid tracking number - please verify and try again');
        setTrackingNumber('');
        setIsScanned(false);
        setItemDetails(null);
      }
    } catch (error) {
      setErrorMessage('Error scanning tracking number. Please try again.');
      setTrackingNumber('');
      setIsScanned(false);
      setItemDetails(null);
    }
  };

  const fetchItemFromInventory = async (trackingNum: string): Promise<ItemDetails | null> => {
    // Simulate API call with a delay
    return new Promise((resolve) => {
      setTimeout(() => {
        // Mock inventory data - replace with actual API call
        const mockInventory: { [key: string]: ItemDetails } = {
          'TRK001': {
            item_id: 'ITEM-001',
            description: 'Laptop Computer',
            quantity: 1,
            value: 1200.50,
          },
          'TRK002': {
            item_id: 'ITEM-002',
            description: 'Printer Device',
            quantity: 2,
            value: 450.00,
          },
          'TRK003': {
            item_id: 'ITEM-003',
            description: 'Monitor Display',
            quantity: 3,
            value: 300.75,
          },
        };

        // Return matching item or null
        resolve(mockInventory[trackingNum] || null);
      }, 500);
    });
  };

  const handleFormFieldChange = (fieldName: keyof NSIItemFormData, value: string | number) => {
    setFormData((prev) => ({
      ...prev,
      [fieldName]: value,
    }));
  };

  const handleAddItem = () => {
    // Validate required fields
    if (!formData.trackingNumber.trim()) {
      setErrorMessage('Tracking number is required');
      return;
    }
    if (!formData.item_id.trim()) {
      setErrorMessage('Item ID is required - please scan a valid tracking number');
      return;
    }
    if (!formData.disposition) {
      setErrorMessage('Disposition type is required');
      return;
    }
    if (formData.quantity <= 0) {
      setErrorMessage('Quantity must be greater than 0');
      return;
    }

    // Add item to scanned items list
    setScannedItems((prev) => [...prev, trackingNumber]);

    // Clear form for next item
    handleClear();
  };

  const handleClear = () => {
    setTrackingNumber('');
    setItemDetails(null);
    setIsScanned(false);
    setFormData({
      trackingNumber: '',
      item_id: '',
      description: '',
      disposition: '',
      vendorId: '',
      quantity: 0,
      value: 0,
      location_id: '',
      created_date: new Date().toISOString(),
    });
  };

  return (
    <div style={styles.container}>
      <header style={styles.header}>
        <h1 style={styles.headerH1}>NSI Item Entry</h1>
        <p style={styles.subtitle}>Enter Tracking Number to Add Item</p>
      </header>

      <main style={styles.main}>
        {/* Error Message */}
        {errorMessage && (
          <div style={styles.errorMessage}>
            <span>⚠</span>
            <span>{errorMessage}</span>
          </div>
        )}

        {/* Warning Message */}
        {warningMessage && (
          <div style={styles.warningMessage}>
            <span>!</span>
            <span>{warningMessage}</span>
          </div>
        )}
        {/* Tracking Number Input Section */}
        <section style={styles.section}>
          <div style={styles.formGroup}>
            <label htmlFor="trackingNumber" style={styles.formLabel}>
              Tracking Number <span style={styles.required}>*</span>
            </label>
            <div style={styles.inputGroup}>
              <input
                id="trackingNumber"
                type="text"
                style={styles.trackingInput}
                placeholder="Enter or scan tracking number"
                value={trackingNumber}
                onChange={handleTrackingNumberChange}
              />
              <button
                style={{ ...styles.button, ...styles.btnPrimary }}
                onClick={handleScanClick}
              >
                Scan
              </button>
            </div>
          </div>
        </section>

        {/* NSI Item Form Section */}
        <section style={styles.section}>
          <h2 style={styles.sectionTitle}>NSI Item Information</h2>

          {/* Row 1: Auto-Populated Fields */}
          <div style={styles.formRow}>
            <div style={styles.formGroup}>
              <label htmlFor="item_idDisplay" style={styles.formLabel}>
                Item ID <span style={styles.required}>*</span>
              </label>
              <input
                id="item_idDisplay"
                type="text"
                style={{...styles.formInput, backgroundColor: '#e8e8e8', cursor: 'not-allowed', color: '#555'}}
                placeholder="Auto-populated from scan"
                value={formData.item_id}
                readOnly
              />
            </div>

            <div style={styles.formGroup}>
              <label htmlFor="descriptionDisplay" style={styles.formLabel}>
                Description <span style={styles.required}>*</span>
              </label>
              <input
                id="descriptionDisplay"
                type="text"
                style={{...styles.formInput, backgroundColor: '#e8e8e8', cursor: 'not-allowed', color: '#555'}}
                placeholder="Auto-populated from scan"
                value={formData.description}
                readOnly
              />
            </div>
          </div>

          {/* Row 2: Auto-Populated Fields */}
          <div style={styles.formRow}>
            <div style={styles.formGroup}>
              <label htmlFor="quantityDisplay" style={styles.formLabel}>
                Inventory Quantity <span style={styles.required}>*</span>
              </label>
              <input
                id="quantityDisplay"
                type="number"
                style={{...styles.formInput, backgroundColor: '#e8e8e8', cursor: 'not-allowed', color: '#555'}}
                placeholder="Auto-populated from scan"
                value={formData.quantity}
                readOnly
              />
            </div>

            <div style={styles.formGroup}>
              <label htmlFor="valueDisplay" style={styles.formLabel}>
                Value <span style={styles.required}>*</span>
              </label>
              <input
                id="valueDisplay"
                type="text"
                style={{...styles.formInput, backgroundColor: '#e8e8e8', cursor: 'not-allowed', color: '#555'}}
                placeholder="Auto-populated from scan"
                value={`$${formData.value.toFixed(2)}`}
                readOnly
              />
            </div>
          </div>

          {/* Row 3: Editable Fields */}
          <div style={styles.formRow}>
            <div style={styles.formGroup}>
              <label htmlFor="disposition" style={styles.formLabel}>
                Disposition Type <span style={styles.required}>*</span>
              </label>
              <select
                id="disposition"
                style={styles.formInput}
                value={formData.disposition}
                onChange={(e) => handleFormFieldChange('disposition', e.target.value)}
              >
                <option value="">Select Disposition Type</option>
                <option value="RTV">RTV</option>
                <option value="HAZMAT">HAZMAT</option>
                <option value="REPAIR">REPAIR</option>
              </select>
            </div>

            <div style={styles.formGroup}>
              <label htmlFor="vendorId" style={styles.formLabel}>
                Vendor ID
              </label>
              <input
                id="vendorId"
                type="text"
                style={styles.formInput}
                placeholder="Enter vendor ID"
                value={formData.vendorId}
                onChange={(e) => handleFormFieldChange('vendorId', e.target.value)}
              />
            </div>
          </div>

          {/* Row 4: Editable Fields */}
          <div style={styles.formRow}>
            <div style={styles.formGroup}>
              <label htmlFor="nsiQuantity" style={styles.formLabel}>
                NSI Quantity <span style={styles.required}>*</span>
              </label>
              <input
                id="nsiQuantity"
                type="number"
                style={styles.formInput}
                placeholder="Enter quantity for NSI"
                value={formData.quantity}
                onChange={(e) => handleFormFieldChange('quantity', parseInt(e.target.value, 10) || 0)}
              />
            </div>

            <div style={styles.formGroup}>
              <label htmlFor="location_id" style={styles.formLabel}>
                Location ID
              </label>
              <input
                id="location_id"
                type="text"
                style={styles.formInput}
                placeholder="Enter location ID"
                value={formData.location_id}
                onChange={(e) => handleFormFieldChange('location_id', e.target.value)}
              />
            </div>
          </div>
        </section>

        {/* Action Buttons */}
        <section style={styles.actionButtons}>
          <button
            style={{ ...styles.button, ...styles.btnSuccess }}
            onClick={handleAddItem}
          >
            Add Item
          </button>
          <button
            style={{ ...styles.button, ...styles.btnSecondary }}
            onClick={handleClear}
          >
            Clear
          </button>
        </section>
      </main>
    </div>
  );
};

export default NSIItemEntry;
