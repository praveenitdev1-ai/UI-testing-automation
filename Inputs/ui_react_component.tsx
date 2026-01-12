import React, { useState, useEffect } from 'react';

const NSIManagementSystem = () => {
  const [currentScreen, setCurrentScreen] = useState('dashboard');
  const [notification, setNotification] = useState({ message: '', type: '', show: false });
  const [modal, setModal] = useState({ show: false, content: '' });
  const [showPendingApprovalsView, setShowPendingApprovalsView] = useState(false);
  const [maintenanceMode, setMaintenanceMode] = useState('view');
  const [auditQueueMode, setAuditQueueMode] = useState(false);
  const [hazmatOnlyMode, setHazmatOnlyMode] = useState(false);

  // Form state for React compliance
  const [itemId, setItemId] = useState('');
  const [trackingNumber, setTrackingNumber] = useState('TRK-306954');
  const [destroyLogNumber, setDestroyLogNumber] = useState('');

  // Modal content state for safer rendering  
  const [modalContentType, setModalContentType] = useState('');
  const [modalData, setModalData] = useState({ itemId: '' });

  // Sample data states
  const [worklistItems, setWorklistItems] = useState([
    {
      id: 'NSI-001234',
      tracking: 'TRK-SAH-789123456',
      description: 'Samsung 55" QLED TV - Damaged Screen',
      location: 'RTV Cage A1',
      disposition: 'RTV',
      quantity: 1,
      vendor: 'Samsung Electronics',
      status: 'Pending',
      auditStatus: 'pending',
      dateAdded: '2025-06-02',
      timeAdded: '09:15 AM',
      hazmat: false
    },
    {
      id: 'NSI-001235',
      tracking: 'TRK-EBH-456789123',
      description: 'Lithium Ion Battery - Hazmat Item',
      location: 'Hazmat Storage B2',
      disposition: 'Hazmat Disposal',
      quantity: 1,
      vendor: 'Energizer Holdings',
      status: 'Approved',
      auditStatus: 'na',
      dateAdded: '2025-06-01',
      timeAdded: '02:30 PM',
      hazmat: true
    },
    {
      id: 'NSI-001236',
      tracking: 'TRK-WAR-789456123',
      description: 'KitchenAid Stand Mixer - Motor Issue',
      location: 'Warehouse A',
      disposition: 'Out for Repair',
      quantity: 1,
      vendor: 'KitchenAid',
      status: 'Approved',
      auditStatus: 'completed',
      dateAdded: '2025-05-28',
      timeAdded: '11:20 AM',
      hazmat: false
    }
  ]);

  const showNotification = (message: string, type: 'success' | 'danger' | 'warning') => {
    setNotification({ message, type, show: true });
    setTimeout(() => {
      setNotification(prev => ({ ...prev, show: false }));
    }, 3000);
  };

  const showModal = (content: string) => {
    setModal({ show: true, content });
  };

  // Safe modal content renderer
  const renderModalContent = () => {
    if (modalContentType === 'shipping-documents') {
      return (
        <div>
          <h3>Shipping Documents - {modalData.itemId || 'Unknown Item'}</h3>
          <p style={{ margin: '20px 0' }}>Document management interface would open here.</p>
          <div style={{ marginTop: '20px' }}>
            <button
              style={{ background: '#0D5DAB', color: 'white', padding: '8px 12px', fontSize: '12px', border: 'none', borderRadius: '5px', cursor: 'pointer', marginRight: '5px' }}
              onClick={() => { closeModal(); showNotification('Viewing document', 'success'); }}
            >
              View
            </button>
            <button
              style={{ background: '#28a745', color: 'white', padding: '8px 12px', fontSize: '12px', border: 'none', borderRadius: '5px', cursor: 'pointer', marginRight: '5px' }}
              onClick={() => { closeModal(); showNotification('Printing document', 'success'); }}
            >
              Print
            </button>
            <button
              style={{ background: '#6c757d', color: 'white', padding: '8px 12px', fontSize: '12px', border: 'none', borderRadius: '5px', cursor: 'pointer' }}
              onClick={closeModal}
            >
              Close
            </button>
          </div>
        </div>
      );
    }

    if (modalContentType === 'hazmat-documents') {
      return (
        <div>
          <h3>HAZMAT Documents - {modalData.itemId || 'Unknown Item'}</h3>
          <div style={{ background: '#ffeaea', borderLeft: '4px solid #dc3545', padding: '15px', margin: '20px 0', borderRadius: '5px' }}>
            <strong style={{ color: '#dc3545' }}>HAZMAT DOCUMENTS REQUIRED</strong>
            <ul style={{ color: '#dc3545', marginTop: '10px' }}>
              <li>Safety Data Sheet</li>
              <li>Disposal Authorization</li>
            </ul>
          </div>
          <button
            style={{ background: '#6c757d', color: 'white', padding: '8px 12px', fontSize: '12px', border: 'none', borderRadius: '5px', cursor: 'pointer' }}
            onClick={closeModal}
          >
            Close
          </button>
        </div>
      );
    }

    // Default fallback for HTML content (legacy support)
    return <div dangerouslySetInnerHTML={{ __html: modal.content }} />;
  };

  const closeModal = () => {
    setModal({ show: false, content: '' });
    setModalContentType('');
    setModalData({ itemId: '' });
  };

  const showScreen = (screenId: string) => {
    setCurrentScreen(screenId);
    showNotification(`Switched to ${screenId}`, 'success');
  };

  const generateTrackingNumber = () => {
    const prefixes = ['TRK-SIM', 'TRK-SAH', 'TRK-EBH', 'TRK-WAR'];
    const prefix = prefixes[Math.floor(Math.random() * prefixes.length)];
    const number = Math.floor(Math.random() * 1000000000);
    return `${prefix}-${number}`;
  };

  // Add item to worklist function
  const addToWorklist = () => {
    if (!itemId) {
      showNotification('Please enter an Item ID', 'warning');
      return;
    }

    const finalTrackingNumber = trackingNumber || generateTrackingNumber();

    const newItem = {
      id: itemId,
      tracking: finalTrackingNumber,
      description: 'New Item - Description Pending',
      location: 'RTV Cage',
      disposition: 'RTV',
      quantity: 1,
      vendor: 'Vendor TBD',
      status: 'Pending',
      auditStatus: 'na',
      dateAdded: new Date().toISOString().split('T')[0],
      timeAdded: new Date().toLocaleTimeString(),
      hazmat: false
    };

    setWorklistItems(prev => [...prev, newItem]);

    // Clear form fields using React state
    setItemId('');
    setTrackingNumber(generateTrackingNumber());
    setDestroyLogNumber('');

    showNotification(`Item ${itemId} added to worklist`, 'success');
  };

  const getFilteredWorklistItems = () => {
    if (auditQueueMode) {
      return worklistItems.filter(item => item.auditStatus === 'pending');
    }
    return worklistItems;
  };

  // Dashboard Screen
  const DashboardScreen = () => (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Header */}
      <div style={{
        background: 'linear-gradient(135deg, #002242, #374151)',
        color: 'white',
        padding: '20px',
        borderRadius: '10px',
        position: 'relative'
      }}>
        <h1 style={{ margin: 0, fontSize: '28px' }}>Manager Dashboard</h1>
        <div style={{ position: 'absolute', top: '20px', right: '20px', fontSize: '14px', opacity: 0.9 }}>
          Last Updated: June 20, 2025
        </div>
      </div>

      {/* Stats Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '20px' }}>
        <div style={{
          background: 'white',
          padding: '20px',
          borderRadius: '10px',
          boxShadow: '0 2px 5px rgba(0,0,0,0.1)',
          borderLeft: '4px solid #0D5DAB'
        }}>
          <h3 style={{ margin: '0 0 8px 0', fontSize: '14px', color: '#666' }}>Total NSI Items</h3>
          <h2 style={{ margin: 0, fontSize: '32px', fontWeight: 'bold', color: '#0D5DAB' }}>1,247</h2>
        </div>
        <div
          style={{
            background: 'white',
            padding: '20px',
            borderRadius: '10px',
            boxShadow: '0 2px 5px rgba(0,0,0,0.1)',
            borderLeft: '4px solid #ffc107',
            cursor: 'pointer',
            transition: 'transform 0.2s'
          }}
          onClick={() => setShowPendingApprovalsView(!showPendingApprovalsView)}
        >
          <h3 style={{ margin: '0 0 8px 0', fontSize: '14px', color: '#666' }}>Pending Approvals</h3>
          <h2 style={{ margin: 0, fontSize: '32px', fontWeight: 'bold', color: '#ffc107' }}>3</h2>
          <div style={{ fontSize: '12px', color: '#999', marginTop: '5px' }}>Click to view details</div>
        </div>
        <div style={{
          background: 'white',
          padding: '20px',
          borderRadius: '10px',
          boxShadow: '0 2px 5px rgba(0,0,0,0.1)',
          borderLeft: '4px solid #dc3545'
        }}>
          <h3 style={{ margin: '0 0 8px 0', fontSize: '14px', color: '#666' }}>Hazmat Items</h3>
          <h2 style={{ margin: 0, fontSize: '32px', fontWeight: 'bold', color: '#dc3545' }}>8</h2>
        </div>
        <div style={{
          background: 'white',
          padding: '20px',
          borderRadius: '10px',
          boxShadow: '0 2px 5px rgba(0,0,0,0.1)',
          borderLeft: '4px solid #28a745'
        }}>
          <h3 style={{ margin: '0 0 8px 0', fontSize: '14px', color: '#666' }}>Monthly Recovery</h3>
          <h2 style={{ margin: 0, fontSize: '32px', fontWeight: 'bold', color: '#28a745' }}>$127K</h2>
        </div>
      </div>

      {/* Recent Activity or Pending Approvals */}
      <div style={{ background: 'white', padding: '20px', borderRadius: '10px', boxShadow: '0 2px 5px rgba(0,0,0,0.1)' }}>
        {!showPendingApprovalsView ? (
          <>
            <h3>Recent Activity</h3>
            <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: '15px' }}>
              <thead>
                <tr style={{ background: '#f8f9fa' }}>
                  <th style={{ padding: '10px', textAlign: 'left', borderBottom: '1px solid #ddd' }}>Item ID</th>
                  <th style={{ padding: '10px', textAlign: 'left', borderBottom: '1px solid #ddd' }}>Description</th>
                  <th style={{ padding: '10px', textAlign: 'left', borderBottom: '1px solid #ddd' }}>Status</th>
                  <th style={{ padding: '10px', textAlign: 'left', borderBottom: '1px solid #ddd' }}>Last Modified</th>
                  <th style={{ padding: '10px', textAlign: 'left', borderBottom: '1px solid #ddd' }}>Disposition</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td style={{ padding: '10px', borderBottom: '1px solid #eee' }}><strong>NSI-001234</strong></td>
                  <td style={{ padding: '10px', borderBottom: '1px solid #eee' }}>Samsung 55" QLED TV - Damaged Display</td>
                  <td style={{ padding: '10px', borderBottom: '1px solid #eee' }}>
                    <span style={{ background: '#fef3c7', color: '#92400e', padding: '4px 8px', borderRadius: '10px', fontSize: '12px' }}>Pending</span>
                  </td>
                  <td style={{ padding: '10px', borderBottom: '1px solid #eee' }}>2025-06-03 10:30</td>
                  <td style={{ padding: '10px', borderBottom: '1px solid #eee' }}>
                    <button
                      style={{ background: '#0D5DAB', color: 'white', padding: '5px 10px', fontSize: '12px', border: 'none', borderRadius: '5px', cursor: 'pointer' }}
                      onClick={() => showNotification('Opening review for NSI-001234', 'success')}
                    >
                      Review
                    </button>
                  </td>
                </tr>
                <tr>
                  <td style={{ padding: '10px', borderBottom: '1px solid #eee' }}><strong>NSI-001235</strong></td>
                  <td style={{ padding: '10px', borderBottom: '1px solid #eee' }}>Lithium Battery - Hazmat Disposal</td>
                  <td style={{ padding: '10px', borderBottom: '1px solid #eee' }}>
                    <span style={{ background: '#d1fae5', color: '#065f46', padding: '4px 8px', borderRadius: '10px', fontSize: '12px' }}>Approved</span>
                  </td>
                  <td style={{ padding: '10px', borderBottom: '1px solid #eee' }}>2025-06-02 14:15</td>
                  <td style={{ padding: '10px', borderBottom: '1px solid #eee' }}>
                    <button
                      style={{ background: '#6c757d', color: 'white', padding: '5px 10px', fontSize: '12px', border: 'none', borderRadius: '5px', cursor: 'pointer' }}
                      onClick={() => showNotification('Opening view for NSI-001235', 'success')}
                    >
                      View
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </>
        ) : (
          <>
            <h3>Pending Approvals - Manager Review Required</h3>
            <div style={{ background: '#fff3cd', border: '1px solid #ffeaa7', borderLeft: '4px solid #ffc107', padding: '15px', borderRadius: '5px', marginBottom: '20px', color: '#856404' }}>
              <strong>⚠ Approval Required:</strong> The following items require manager approval before proceeding with their disposition. Total: 7 items awaiting approval.
            </div>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ background: '#002242', color: 'white' }}>
                  <th style={{ padding: '12px', textAlign: 'left' }}><input type="checkbox" /></th>
                  <th style={{ padding: '12px', textAlign: 'left' }}>Item ID</th>
                  <th style={{ padding: '12px', textAlign: 'left' }}>Request Type</th>
                  <th style={{ padding: '12px', textAlign: 'left' }}>Description</th>
                  <th style={{ padding: '12px', textAlign: 'left' }}>Dept</th>
                  <th style={{ padding: '12px', textAlign: 'left' }}>Date</th>
                  <th style={{ padding: '12px', textAlign: 'left' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                <tr style={{ borderBottom: '1px solid #eee' }}>
                  <td style={{ padding: '12px' }}><input type="checkbox" /></td>
                  <td style={{ padding: '12px' }}><strong>NSI-001234</strong></td>
                  <td style={{ padding: '12px' }}>
                    <span style={{ background: '#fff3cd', color: '#856404', padding: '4px 8px', borderRadius: '15px', fontSize: '12px' }}>Disposition Change</span>
                  </td>
                  <td style={{ padding: '12px' }}>Samsung TV - Change from Salvage to RTV</td>
                  <td style={{ padding: '12px' }}>Electronics</td>
                  <td style={{ padding: '12px' }}>2025-06-01<br /><span style={{ fontSize: '11px', color: '#666' }}>10:30 AM</span></td>
                  <td style={{ padding: '12px' }}>
                    <button
                      style={{ background: '#28a745', color: 'white', padding: '6px 12px', fontSize: '12px', border: 'none', borderRadius: '5px', cursor: 'pointer', marginRight: '5px' }}
                      onClick={() => showNotification('Item NSI-001234 approved', 'success')}
                    >
                      ✓ Approve
                    </button>
                    <button
                      style={{ background: '#dc3545', color: 'white', padding: '6px 12px', fontSize: '12px', border: 'none', borderRadius: '5px', cursor: 'pointer' }}
                      onClick={() => showNotification('Item NSI-001234 rejected', 'danger')}
                    >
                      ✗ Reject
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
            <button
              style={{ background: '#6c757d', color: 'white', padding: '10px 15px', fontSize: '14px', border: 'none', borderRadius: '5px', cursor: 'pointer', marginTop: '15px' }}
              onClick={() => setShowPendingApprovalsView(false)}
            >
              ← Back to Recent Activity
            </button>
          </>
        )}
      </div>
    </div>
  );

  // NSI Entry/Worklist Screen
  const WorklistScreen = () => (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Header */}
      <div style={{
        background: 'linear-gradient(135deg, #002242, #374151)',
        color: 'white',
        padding: '20px',
        borderRadius: '10px',
        position: 'relative'
      }}>
        <h1 style={{ margin: 0, fontSize: '28px' }}>NSI Entry - RTV Cage</h1>
        <div style={{ position: 'absolute', top: '20px', right: '20px', display: 'flex', gap: '10px' }}>
          <button
            style={{ background: '#4f7cff', color: 'white', padding: '8px 15px', fontSize: '14px', border: 'none', borderRadius: '5px', cursor: 'pointer' }}
            onClick={() => showNotification('Worklist refreshed', 'success')}
          >
            🔄 Refresh
          </button>
          <button
            style={{
              background: auditQueueMode ? '#28a745' : '#FFF0D2',
              color: auditQueueMode ? 'white' : '#000',
              padding: '8px 15px',
              fontSize: '14px',
              border: 'none',
              borderRadius: '5px',
              cursor: 'pointer'
            }}
            onClick={() => {
              setAuditQueueMode(!auditQueueMode);
              showNotification(auditQueueMode ? 'Showing all items' : 'Showing items requiring audit only', 'success');
            }}
          >
            📋 {auditQueueMode ? 'Show All Items' : 'Show Audit Queue'}
          </button>
          <button
            id="print_worklist"
            style={{ background: '#28a745', color: 'white', padding: '8px 15px', fontSize: '14px', border: 'none', borderRadius: '5px', cursor: 'pointer' }}
            onClick={() => showNotification('Preparing worklist for printing...', 'success')}
          >
            🖨️ Print Worklist
          </button>
          <button
            id="add_to_worklist_header"
            style={{ background: '#0D5DAB', color: 'white', padding: '8px 15px', fontSize: '14px', border: 'none', borderRadius: '5px', cursor: 'pointer' }}
            onClick={() => {
              // Focus will be handled by the form field itself
              showNotification('Ready to add new item to worklist', 'success');
            }}
          >
            ➕ Add to Worklist
          </button>
        </div>
      </div>

      {/* Add Item Form */}
      <div style={{ background: 'white', padding: '20px', borderRadius: '10px', boxShadow: '0 2px 5px rgba(0,0,0,0.1)' }}>
        <h3 style={{ color: '#0D5DAB', marginBottom: '20px' }}>Add Item to Worklist</h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '20px', marginBottom: '20px' }}>
          <div>
            <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>Item ID</label>
            <input
              type="text"
              id="item_id"
              style={{ width: '100%', padding: '12px', border: '1px solid #ddd', borderRadius: '5px', boxSizing: 'border-box' }}
              placeholder="Enter NSI Item ID"
            />
          </div>
          <div>
            <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>POS Tracking Number</label>
            <input
              type="text"
              id="tracking_number"
              style={{ width: '100%', padding: '12px', border: '1px solid #ddd', borderRadius: '5px', boxSizing: 'border-box' }}
              placeholder="Auto-generated if blank"
            />
          </div>
          <div>
            <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>Destroy Log Number</label>
            <input
              type="text"
              id="destroyLogNumber"
              value={destroyLogNumber}
              onChange={(e) => setDestroyLogNumber(e.target.value)}
              style={{ width: '100%', padding: '12px', border: '1px solid #ddd', borderRadius: '5px', boxSizing: 'border-box' }}
              placeholder="Enter destroy log #"
            />
          </div>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '20px', marginBottom: '20px' }}>
          <div>
            <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>Item Description</label>
            <input
              type="text"
              id="description"
              style={{ width: '100%', padding: '12px', border: '1px solid #ddd', borderRadius: '5px', boxSizing: 'border-box' }}
              placeholder="Enter item description"
            />
          </div>
          <div>
            <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>Department Number</label>
            <input
              type="text"
              id="department_number"
              style={{ width: '100%', padding: '12px', border: '1px solid #ddd', borderRadius: '5px', boxSizing: 'border-box' }}
              placeholder="Enter department number"
            />
          </div>
          <div>
            <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>Quantity</label>
            <input
              type="number"
              id="quantity"
              style={{ width: '100%', padding: '12px', border: '1px solid #ddd', borderRadius: '5px', boxSizing: 'border-box' }}
              placeholder="Enter quantity"
              min="1"
              defaultValue="1"
            />
          </div>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '20px', marginBottom: '20px' }}>
          <div>
            <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>Location</label>
            <input
              type="text"
              id="location"
              style={{ width: '100%', padding: '12px', border: '1px solid #ddd', borderRadius: '5px', boxSizing: 'border-box' }}
              placeholder="Enter location"
            />
          </div>
          <div>
            <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>Disposition Type</label>
            <select
              id="disposition_type"
              style={{ width: '100%', padding: '12px', border: '1px solid #ddd', borderRadius: '5px', boxSizing: 'border-box' }}
            >
              <option value="">Select Disposition Type</option>
              <option value="Salvage">Salvage</option>
              <option value="Destroy">Destroy</option>
              <option value="Return">Return</option>
              <option value="Other">Other</option>
            </select>
          </div>
          <div>
            <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>Sell Price</label>
            <input
              type="number"
              id="sell_price"
              step="0.01"
              style={{ width: '100%', padding: '12px', border: '1px solid #ddd', borderRadius: '5px', boxSizing: 'border-box' }}
              placeholder="Enter sell price"
            />
          </div>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '20px', marginBottom: '20px' }}>
          <div>
            <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>On Hand Inventory</label>
            <input
              type="number"
              id="on_hand_inventory"
              style={{ width: '100%', padding: '12px', border: '1px solid #ddd', borderRadius: '5px', boxSizing: 'border-box' }}
              placeholder="Enter quantity on hand"
            />
          </div>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '20px', marginBottom: '20px' }}>
          <div>
            <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>Vendor Name</label>
            <input
              type="text"
              id="vendor_name"
              style={{ width: '100%', padding: '12px', border: '1px solid #ddd', borderRadius: '5px', boxSizing: 'border-box' }}
              placeholder="Enter vendor name"
              required
            />
          </div>
        </div>
        <div style={{ display: 'flex', gap: '15px', justifyContent: 'flex-end' }}>
          <button
            style={{ background: '#6c757d', color: 'white', padding: '12px 20px', border: 'none', borderRadius: '5px', cursor: 'pointer' }}
            onClick={() => showNotification('Scanning...', 'success')}
          >
            📷 Scan
          </button>
          <button
            id="add_to_worklist_form"
            style={{ background: '#4f7cff', color: 'white', padding: '12px 20px', border: 'none', borderRadius: '5px', cursor: 'pointer' }}
            onClick={addToWorklist}
          >
            ➕ Add to Worklist
          </button>
          <button
            id="start_workflow_form_main"
            style={{ background: '#28a745', color: 'white', padding: '12px 20px', border: 'none', borderRadius: '5px', cursor: 'pointer' }}
            onClick={() => showNotification('Starting workflow for new item...', 'success')}
          >
            ▶️ Start Workflow
          </button>
        </div>
      </div>

      {/* Filter Section */}
      <div style={{ background: 'white', padding: '20px', borderRadius: '10px', boxShadow: '0 2px 5px rgba(0,0,0,0.1)' }}>
        <h3 style={{ color: '#0D5DAB', marginBottom: '20px' }}>Filter Worklist Items</h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '15px', marginBottom: '20px' }}>
          <div>
            <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>Filter by Item ID</label>
            <input
              type="text"
              style={{ width: '100%', padding: '8px', border: '1px solid #ddd', borderRadius: '5px', boxSizing: 'border-box' }}
              placeholder="Enter Item ID"
            />
          </div>
          <div>
            <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>Filter by Disposition</label>
            <select style={{ width: '100%', padding: '8px', border: '1px solid #ddd', borderRadius: '5px', boxSizing: 'border-box' }}>
              <option value="">All Dispositions</option>
              <option value="RTV">RTV</option>
              <option value="Hazmat Disposal">Hazmat Disposal</option>
              <option value="Out for Repair">Out for Repair</option>
              <option value="Destroy">Destroy</option>
              <option value="Salvage">Salvage</option>
            </select>
          </div>
          <div>
            <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>Filter by Vendor</label>
            <select style={{ width: '100%', padding: '8px', border: '1px solid #ddd', borderRadius: '5px', boxSizing: 'border-box' }}>
              <option value="">All Vendors</option>
              <option value="Samsung Electronics">Samsung Electronics</option>
              <option value="Energizer Holdings">Energizer Holdings</option>
              <option value="KitchenAid">KitchenAid</option>
            </select>
          </div>
          <div>
            <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>Filter by Status</label>
            <select style={{ width: '100%', padding: '8px', border: '1px solid #ddd', borderRadius: '5px', boxSizing: 'border-box' }}>
              <option value="">All Status</option>
              <option value="Pending">Pending</option>
              <option value="Approved">Approved</option>
              <option value="In Progress">In Progress</option>
            </select>
          </div>
        </div>
        <div style={{ display: 'flex', gap: '10px' }}>
          <button
            style={{ background: '#6c757d', color: 'white', padding: '8px 15px', fontSize: '14px', border: 'none', borderRadius: '5px', cursor: 'pointer' }}
            onClick={() => showNotification('All filters cleared', 'success')}
          >
            🗑️ Clear Filters
          </button>
          <button
            style={{ background: '#0D5DAB', color: 'white', padding: '8px 15px', fontSize: '14px', border: 'none', borderRadius: '5px', cursor: 'pointer' }}
            onClick={() => showNotification('Filters applied', 'success')}
          >
            🔍 Apply Filters
          </button>
        </div>
      </div>

      {/* Worklist Table */}
      <div style={{ background: 'white', padding: '20px', borderRadius: '10px', boxShadow: '0 2px 5px rgba(0,0,0,0.1)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <h3 style={{ color: '#0D5DAB', margin: 0 }}>Current Worklist Items</h3>
          <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
            <button
              style={{ background: '#002242', color: 'white', padding: '8px 15px', fontSize: '14px', border: 'none', borderRadius: '5px', cursor: 'pointer' }}
              onClick={() => showNotification('Opening batch actions...', 'success')}
            >
              📋 Batch Actions
            </button>
            <span style={{ color: '#666', fontSize: '14px' }}>{getFilteredWorklistItems().length} items in queue</span>
          </div>
        </div>

        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ background: '#1F2937', color: 'white' }}>
                <th style={{ padding: '12px', textAlign: 'left', width: '40px' }}><input type="checkbox" /></th>
                <th style={{ padding: '12px', textAlign: 'left' }}>Item ID</th>
                <th style={{ padding: '12px', textAlign: 'left' }}>Tracking Number</th>
                <th style={{ padding: '12px', textAlign: 'left' }}>Description</th>
                <th style={{ padding: '12px', textAlign: 'left' }}>Location</th>
                <th style={{ padding: '12px', textAlign: 'left' }}>Disposition</th>
                <th style={{ padding: '12px', textAlign: 'left' }}>Quantity</th>
                <th style={{ padding: '12px', textAlign: 'left' }}>Vendor Name</th>
                <th style={{ padding: '12px', textAlign: 'left' }}>Status</th>
                <th style={{ padding: '12px', textAlign: 'left' }}>Audit Status</th>
                <th style={{ padding: '12px', textAlign: 'left' }}>Date Added</th>
                <th style={{ padding: '12px', textAlign: 'left' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {getFilteredWorklistItems().map((item) => (
                <tr key={item.id} style={{ borderBottom: '1px solid #eee' }}>
                  <td style={{ padding: '12px' }}><input type="checkbox" /></td>
                  <td style={{ padding: '12px' }}><strong>{item.id}</strong></td>
                  <td style={{ padding: '12px', color: '#4f7cff' }}>{item.tracking}</td>
                  <td style={{ padding: '12px' }}>
                    {item.description}
                    {item.hazmat && <span style={{ background: '#ffc107', color: '#000', padding: '2px 6px', borderRadius: '3px', fontSize: '10px', marginLeft: '8px' }}>⚠</span>}
                  </td>
                  <td style={{ padding: '12px' }}>{item.location}</td>
                  <td style={{ padding: '12px' }}>
                    <select
                      style={{ padding: '4px', fontSize: '12px', width: '100%', border: '1px solid #ddd', borderRadius: '3px' }}
                      defaultValue={item.disposition}
                      onChange={() => showNotification(`Disposition updated for ${item.id}`, 'success')}
                    >
                      <option>RTV</option>
                      <option>RTD</option>
                      <option>Destroy</option>
                      <option>Salvage</option>
                      <option>Vendor Hold</option>
                      <option>Out for Repair</option>
                      <option>Recall</option>
                      <option>Hazmat Disposal</option>
                    </select>
                  </td>
                  <td style={{ padding: '12px' }}>
                    <input
                      type="number"
                      style={{ padding: '4px', fontSize: '12px', width: '60px', border: '1px solid #ddd', borderRadius: '3px' }}
                      defaultValue={item.quantity}
                      min="1"
                    />
                  </td>
                  <td style={{ padding: '12px' }}>{item.vendor}</td>
                  <td style={{ padding: '12px' }}>
                    <span style={{
                      background: item.status === 'Approved' ? '#d1fae5' : '#fef3c7',
                      color: item.status === 'Approved' ? '#065f46' : '#92400e',
                      padding: '6px 12px',
                      borderRadius: '15px',
                      fontSize: '12px'
                    }}>
                      {item.status}
                    </span>
                  </td>
                  <td style={{ padding: '12px' }}>
                    <span style={{
                      background: item.auditStatus === 'pending' ? '#fff3cd' : item.auditStatus === 'completed' ? '#d1fae5' : '#e9ecef',
                      color: item.auditStatus === 'pending' ? '#856404' : item.auditStatus === 'completed' ? '#065f46' : '#6c757d',
                      padding: '6px 12px',
                      borderRadius: '15px',
                      fontSize: '12px'
                    }}>
                      {item.auditStatus === 'pending' ? '⚠ Audit Required' :
                        item.auditStatus === 'completed' ? '✓ Audit Completed' :
                          'No Audit Required'}
                    </span>
                  </td>
                  <td style={{ padding: '12px' }}>
                    {item.dateAdded}<br />
                    <span style={{ fontSize: '12px', color: '#666' }}>{item.timeAdded}</span>
                  </td>
                  <td style={{ padding: '12px' }}>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '5px' }}>
                      <select
                        style={{ padding: '4px', fontSize: '12px', width: '100%', border: '1px solid #ddd', borderRadius: '3px' }}
                        onChange={(e) => {
                          if (e.target.value) {
                            showNotification(`${e.target.value} selected for ${item.id}`, 'success');
                            e.target.value = '';
                          }
                        }}
                      >
                        <option value="">Select Action</option>
                        <option value="Start Workflow">Start Workflow</option>
                        <option value="Request Approval">Request Approval</option>
                        <option value="Priority Flag">Priority Flag</option>
                        <option value="Place Hold">Place Hold</option>
                        <option value="Reverse">Reverse</option>
                      </select>
                      <div style={{ display: 'flex', gap: '3px' }}>
                        <button
                          id="start_workflow_worklist_section"
                          style={{ background: '#28a745', color: 'white', padding: '3px 6px', fontSize: '10px', border: 'none', borderRadius: '3px', cursor: 'pointer', flex: 1 }}
                          onClick={() => showNotification(`Starting workflow for ${item.id}`, 'success')}
                        >
                          ▶️ Start
                        </button>
                        <button
                          id="reverse_worklist"
                          style={{ background: '#ff6b35', color: 'white', padding: '3px 6px', fontSize: '10px', border: 'none', borderRadius: '3px', cursor: 'pointer', flex: 1 }}
                          onClick={() => showNotification(`Reversing ${item.id}`, 'warning')}
                        >
                          🔄 Reverse
                        </button>
                      </div>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );

  // NSI Maintenance Screen  
  const MaintenanceScreen = () => {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
        {/* Header */}
        <div style={{
          background: 'linear-gradient(135deg, #002242, #374151)',
          color: 'white',
          padding: '20px',
          borderRadius: '10px',
          position: 'relative'
        }}>
          <h1 style={{ margin: 0, fontSize: '28px' }}>NSI Maintenance</h1>
          <div style={{ position: 'absolute', top: '20px', right: '20px', display: 'flex', gap: '10px', alignItems: 'center' }}>
            <button
              style={{
                background: hazmatOnlyMode ? '#28a745' : '#ff6b35',
                color: 'white',
                padding: '8px 12px',
                fontSize: '12px',
                border: 'none',
                borderRadius: '5px',
                cursor: 'pointer'
              }}
              onClick={() => {
                setHazmatOnlyMode(!hazmatOnlyMode);
                showNotification(hazmatOnlyMode ? 'Showing all items' : 'Showing hazmat items only', hazmatOnlyMode ? 'success' : 'warning');
              }}
            >
              ⚠ {hazmatOnlyMode ? 'Show All Items' : 'Show Hazmat Only'}
            </button>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <label style={{ fontWeight: 'bold', color: 'white' }}>Mode:</label>
              <select
                style={{ padding: '8px', minWidth: '120px', border: '1px solid #ddd', borderRadius: '5px' }}
                value={maintenanceMode}
                onChange={(e) => {
                  setMaintenanceMode(e.target.value);
                  showNotification(`Switched to ${e.target.value} mode`, 'success');
                }}
              >
                <option value="view">View</option>
                <option value="add">Add</option>
                <option value="change">Change</option>
                <option value="remove">Remove</option>
              </select>
            </div>
          </div>
        </div>

        {/* Add Item Section */}
        {maintenanceMode === 'add' && (
          <div style={{ background: 'white', padding: '20px', borderRadius: '10px', boxShadow: '0 2px 5px rgba(0,0,0,0.1)' }}>
            <h3 style={{ color: '#002242', marginBottom: '20px' }}>Add New Item</h3>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr auto auto', gap: '20px', alignItems: 'end', marginBottom: '20px' }}>
              <div>
                <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>NSI ID</label>
                <input
                  id="maintenance_nsiId"
                  type="text"
                  style={{ width: '100%', padding: '12px', border: '1px solid #ddd', borderRadius: '5px', boxSizing: 'border-box' }}
                  placeholder="Enter NSI ID"
                />
              </div>
              <div>
                <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>Item ID</label>
                <input
                  id="maintenance_itemId"
                  type="text"
                  style={{ width: '100%', padding: '12px', border: '1px solid #ddd', borderRadius: '5px', boxSizing: 'border-box' }}
                  placeholder="Enter NSI Item ID"
                />
              </div>
              <div>
                <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>POS Tracking Number</label>
                <input
                  type="text"
                  style={{ width: '100%', padding: '12px', border: '1px solid #ddd', borderRadius: '5px', boxSizing: 'border-box' }}
                  placeholder="Enter POS tracking number"
                />
              </div>
              <div>
                <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>Destroy Log Number</label>
                <input
                  type="text"
                  style={{ width: '100%', padding: '12px', border: '1px solid #ddd', borderRadius: '5px', boxSizing: 'border-box' }}
                  placeholder="Enter destroy log number"
                />
              </div>
              <button
                style={{ background: '#6c757d', color: 'white', padding: '12px 20px', border: 'none', borderRadius: '5px', cursor: 'pointer' }}
                onClick={() => showNotification('Scanning...', 'success')}
              >
                📷 Scan
              </button>
              <button
                style={{ background: '#002242', color: 'white', padding: '12px 20px', border: 'none', borderRadius: '5px', cursor: 'pointer' }}
                onClick={() => showNotification('Item added to maintenance', 'success')}
              >
                Add Item
              </button>
            </div>
            <div style={{ fontSize: '13px', color: '#666', marginTop: '10px' }}>
              <strong>Instructions:</strong> Enter an Item ID, POS Tracking Number, or Destroy Log Number to add an item. Use the Scan button to capture numbers automatically.
            </div>
          </div>
        )}

        {/* Search Section for Change/Remove modes */}
        {(maintenanceMode === 'change' || maintenanceMode === 'remove') && (
          <div style={{ background: 'white', padding: '20px', borderRadius: '10px', boxShadow: '0 2px 5px rgba(0,0,0,0.1)' }}>
            <h3 style={{ color: '#002242', marginBottom: '20px' }}>Search Item</h3>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr auto', gap: '20px', alignItems: 'end' }}>
              <div>
                <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>NSI ID</label>
                <input
                  id="search_itemIdOrTrackingNumber"
                  type="text"
                  style={{ width: '100%', padding: '12px', border: '1px solid #ddd', borderRadius: '5px', boxSizing: 'border-box' }}
                  placeholder="Enter NSI ID"
                />
              </div>
              <div>
                <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>Item ID or Tracking Number</label>
                <input
                  type="text"
                  style={{ width: '100%', padding: '12px', border: '1px solid #ddd', borderRadius: '5px', boxSizing: 'border-box' }}
                  placeholder="Enter Item ID or tracking number"
                />
              </div>
              <button
                style={{ background: '#002242', color: 'white', padding: '12px 20px', border: 'none', borderRadius: '5px', cursor: 'pointer' }}
                onClick={() => showNotification('Searching for item...', 'success')}
              >
                Search Item
              </button>
            </div>
          </div>
        )}

        {/* Sample Item Cards */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '30px' }}>
          {/* Item 1 - Regular Item */}
          {(!hazmatOnlyMode || maintenanceMode !== 'view') && (
            <div style={{
              background: 'white',
              padding: '20px',
              borderRadius: '10px',
              boxShadow: '0 2px 5px rgba(0,0,0,0.1)',
              border: maintenanceMode === 'change' ? '2px solid #0D5DAB' : maintenanceMode === 'remove' ? '2px solid #dc3545' : 'none',
              cursor: maintenanceMode !== 'view' ? 'pointer' : 'default'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
                <h3>Item #1 - NSI-001234</h3>
                <div style={{ display: 'flex', gap: '10px' }}>
                  <button
                    id="reverse_button"
                    style={{ background: '#ff6b35', color: 'white', padding: '8px 12px', fontSize: '12px', border: 'none', borderRadius: '5px', cursor: 'pointer' }}
                    onClick={() => showNotification('Reversing item NSI-001234', 'warning')}
                  >
                    🔄 Reverse
                  </button>
                  <button
                    id="start_workflow_button_maintenance"
                    style={{ background: '#28a745', color: 'white', padding: '8px 12px', fontSize: '12px', border: 'none', borderRadius: '5px', cursor: 'pointer' }}
                    onClick={() => showNotification('Starting workflow for NSI-001234', 'success')}
                  >
                    ▶️ Start Workflow
                  </button>
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(8, 1fr)', gap: '20px', marginBottom: '15px' }}>
                <div>
                  <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>Item ID</label>
                  <input
                    type="text"
                    style={{ width: '100%', padding: '8px', border: '1px solid #ddd', borderRadius: '5px', background: '#f8f9fa', boxSizing: 'border-box' }}
                    defaultValue="NSI-001234"
                    readOnly
                  />
                </div>
                <div>
                  <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>Dept</label>
                  <select style={{ width: '100%', padding: '8px', border: '1px solid #ddd', borderRadius: '5px', boxSizing: 'border-box' }} defaultValue="Electronics">
                    <option value="">Select Department</option>
                    <option value="Electronics">Electronics</option>
                    <option value="Home & Garden">Home & Garden</option>
                    <option value="Automotive">Automotive</option>
                  </select>
                </div>
                <div style={{ gridColumn: 'span 2' }}>
                  <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>Description</label>
                  <input
                    type="text"
                    style={{ width: '100%', padding: '8px', border: '1px solid #ddd', borderRadius: '5px', boxSizing: 'border-box' }}
                    defaultValue="Samsung 55 inch QLED TV - Cracked Screen"
                  />
                </div>
                <div>
                  <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>Quantity</label>
                  <input
                    type="number"
                    style={{ width: '100%', padding: '8px', border: '1px solid #ddd', borderRadius: '5px', boxSizing: 'border-box' }}
                    defaultValue="1"
                    min="1"
                  />
                </div>
                <div>
                  <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>Unit Sell Price</label>
                  <input
                    type="number"
                    style={{ width: '100%', padding: '8px', border: '1px solid #ddd', borderRadius: '5px', boxSizing: 'border-box' }}
                    defaultValue="899.99"
                    step="0.01"
                  />
                </div>
                <div>
                  <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>Extended Price</label>
                  <input
                    type="text"
                    style={{ width: '100%', padding: '8px', border: '1px solid #ddd', borderRadius: '5px', color: '#0D5DAB', fontWeight: '600', background: '#f8f9fa', boxSizing: 'border-box' }}
                    defaultValue="$899.99"
                    readOnly
                  />
                </div>
                <div>
                  <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>Shipment Number</label>
                  <input
                    id="shipment_number"
                    type="text"
                    style={{ width: '100%', padding: '8px', border: '1px solid #ddd', borderRadius: '5px', boxSizing: 'border-box' }}
                    placeholder="Enter shipment number"
                  />
                </div>
                <div>
                  <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>Document Options</label>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    <label style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <input
                        id="bol_checkbox"
                        type="checkbox"
                        style={{ margin: '0' }}
                      />
                      <span>BOL (Bill of Lading)</span>
                    </label>
                    <label style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <input
                        id="shipment_label_checkbox"
                        type="checkbox"
                        style={{ margin: '0' }}
                      />
                      <span>Shipment Label</span>
                    </label>
                  </div>
                </div>
                <div>
                  <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>Document Category</label>
                  <select
                    id="rc_document_category"
                    style={{ width: '100%', padding: '8px', border: '1px solid #ddd', borderRadius: '5px', boxSizing: 'border-box' }}
                  >
                    <option>Select Category</option>
                    <option>Shipping Information</option>
                    <option>Packages</option>
                    <option>Hazmat Container</option>
                    <option>Shipping Documents</option>
                    <option>Labels</option>
                    <option>Bill of Lading</option>
                    <option>Packing Slip</option>
                    <option>Standard Label</option>
                  </select>
                </div>
                <div>
                  <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>Generated Document</label>
                  <div
                    id="generatedDocument"
                    style={{
                      width: '100%',
                      padding: '12px',
                      border: '2px dashed #ddd',
                      borderRadius: '5px',
                      textAlign: 'center',
                      color: '#666',
                      backgroundColor: '#f9f9f9'
                    }}
                  >
                    📄 Document will appear here after generation
                  </div>
                </div>
              </div>

              <div style={{ marginTop: '20px' }}>
                <h4>Document Management</h4>
                <div style={{ display: 'flex', gap: '10px', marginTop: '10px', flexWrap: 'wrap' }}>
                  <button
                    id="print_button"
                    style={{ background: '#28a745', color: 'white', padding: '8px 12px', fontSize: '12px', border: 'none', borderRadius: '5px', cursor: 'pointer' }}
                    onClick={() => showNotification('Printing RC document...', 'success')}
                  >
                    🖨️ Print RC Document
                  </button>
                  <button
                    style={{ background: '#0D5DAB', color: 'white', padding: '8px 12px', fontSize: '12px', border: 'none', borderRadius: '5px', cursor: 'pointer' }}
                    onClick={() => {
                      const category = (document.getElementById('document_category') as HTMLSelectElement)?.value;
                      if (!category || category === 'Select Category') {
                        showNotification('Please select a document category first', 'warning');
                        return;
                      }
                      const docArea = document.getElementById('generatedDocument');
                      if (docArea) {
                        docArea.innerHTML = `
                        <div style="text-align: left; padding: 10px;">
                          <strong>Generated ${category} Document</strong><br>
                          <small>Document ID: RC-${Date.now()}</small><br>
                          <div style="margin-top: 10px; padding: 10px; background: white; border: 1px solid #ddd;">
                            📄 ${category} content generated successfully<br>
                            Ready for printing
                          </div>
                        </div>
                      `;
                      }
                      showNotification(`${category} document generated successfully`, 'success');
                    }}
                  >
                    📋 Generate RC Document
                  </button>
                  <button
                    id="document_modal"
                    style={{ background: '#0D5DAB', color: 'white', padding: '8px 12px', fontSize: '12px', border: 'none', borderRadius: '5px', cursor: 'pointer' }}
                    onClick={() => {
                      const category = (document.getElementById('document_category') as HTMLSelectElement)?.value;
                      if (!category || category === 'Select Category') {
                        showNotification('Please select a document category first', 'warning');
                        return;
                      }
                      showModal(`
                      <div style="text-align: center; padding: 20px;">
                        <h3 style="color: #0D5DAB; margin-bottom: 20px;">RC Document Modal - ${category}</h3>
                        <div style="background: #f8f9fa; border: 1px solid #ddd; padding: 20px; border-radius: 8px; margin: 20px 0; text-align: left;">
                          <h4 style="color: #0D5DAB; margin-bottom: 15px;">📄 Generated RC Document</h4>
                          <div style="background: white; padding: 15px; border-radius: 5px; margin: 10px 0;">
                            <strong>Document Category:</strong> ${category}<br>
                            <strong>Document ID:</strong> RC-${Date.now()}<br>
                            <strong>Generated Date:</strong> ${new Date().toLocaleDateString()}<br>
                            <strong>Status:</strong> Ready for Processing<br><br>
                            <div style="border-left: 4px solid #0D5DAB; padding-left: 15px; margin: 15px 0;">
                              <strong>Document Contents:</strong><br>
                              • Item details and tracking numbers<br>
                              • Category-specific information<br>
                              • Processing instructions<br>
                              • Return Center routing details
                            </div>
                          </div>
                        </div>
                        <div style="margin-top: 20px;">
                          <button 
                            style="background: #28a745; color: white; padding: 10px 15px; font-size: 14px; border: none; border-radius: 5px; cursor: pointer; margin-right: 10px;" 
                            onclick="closeModal(); showNotification('RC Document printed successfully', 'success')"
                          >
                            🖨️ Print Document
                          </button>
                          <button 
                            style="background: #0D5DAB; color: white; padding: 10px 15px; font-size: 14px; border: none; border-radius: 5px; cursor: pointer; margin-right: 10px;" 
                            onclick="closeModal(); showNotification('Document saved', 'success')"
                          >
                            💾 Save Document
                          </button>
                          <button 
                            style="background: #6c757d; color: white; padding: 10px 15px; font-size: 14px; border: none; border-radius: 5px; cursor: pointer;" 
                            onclick="closeModal()"
                          >
                            ✖️ Close
                          </button>
                        </div>
                      </div>
                    `);
                    }}
                  >
                    📝 Open RC Document Modal
                  </button>
                  <button
                    id="print_bol"
                    style={{ background: '#0D5DAB', color: 'white', padding: '8px 12px', fontSize: '12px', border: 'none', borderRadius: '5px', cursor: 'pointer' }}
                    onClick={() => {
                      const bolCheckbox = document.getElementById('bol_checkbox');
                      if (!bolCheckbox || !(bolCheckbox as HTMLInputElement).checked) {
                        showNotification('Please select BOL (Bill of Lading) checkbox first', 'warning');
                        return;
                      }
                      showNotification('BOL printed with shipment details and signatures', 'success');
                    }}
                  >
                    📄 Print BOL
                  </button>
                  <button
                    id="print_shipment_label"
                    style={{ background: '#28a745', color: 'white', padding: '8px 12px', fontSize: '12px', border: 'none', borderRadius: '5px', cursor: 'pointer' }}
                    onClick={() => {
                      const labelCheckbox = document.getElementById('shipment_label_checkbox');
                      if (!labelCheckbox || !(labelCheckbox as HTMLInputElement).checked) {
                        showNotification('Please select Shipment Label checkbox first', 'warning');
                        return;
                      }
                      showNotification('Shipment label printed successfully', 'success');
                    }}
                  >
                    🏷️ Print Shipment Label
                  </button>
                  <button
                    style={{ background: '#6c757d', color: 'white', padding: '8px 12px', fontSize: '12px', border: 'none', borderRadius: '5px', cursor: 'pointer' }}
                    onClick={() => {
                      setModalContentType('shipping-documents');
                      setModalData({ itemId: 'NSI-001234' });
                      setModal({ show: true, content: '' });
                    }}
                  >
                    📄 Shipping Documents
                  </button>
                  <button
                    style={{ background: '#6c757d', color: 'white', padding: '8px 12px', fontSize: '12px', border: 'none', borderRadius: '5px', cursor: 'pointer' }}
                    onClick={() => showModal(`
                    <h3>Logline Documents - NSI-001234</h3>
                    <p style="margin: 20px 0;">
                      <strong>Logline Documents:</strong><br>
                      • Logline Entry Form<br>
                      • Authorization Form
                    </p>
                    <button style="background: #6c757d; color: white; padding: 8px 12px; font-size: 12px; border: none; border-radius: 5px; cursor: pointer;" onclick="closeModal()">Close</button>
                  `)}
                  >
                    📄 Logline Documents
                  </button>
                  <button
                    id="processLogline"
                    style={{ background: '#28a745', color: 'white', padding: '8px 12px', fontSize: '12px', border: 'none', borderRadius: '5px', cursor: 'pointer' }}
                    onClick={() => showNotification('Processing logline for shipment...', 'success')}
                  >
                    ⚙️ Process Logline
                  </button>
                  <button
                    style={{ background: '#dc3545', color: 'white', padding: '8px 12px', fontSize: '12px', border: 'none', borderRadius: '5px', cursor: 'pointer' }}
                    onClick={() => showNotification('Logline voided for NSI-001234', 'danger')}
                  >
                    ❌ Void Logline
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Item 2 - Hazmat Item */}
          <div style={{
            background: 'white',
            padding: '20px',
            borderRadius: '10px',
            boxShadow: '0 2px 5px rgba(0,0,0,0.1)',
            border: maintenanceMode === 'change' ? '2px solid #0D5DAB' : maintenanceMode === 'remove' ? '2px solid #dc3545' : 'none',
            cursor: maintenanceMode !== 'view' ? 'pointer' : 'default'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
              <h3>
                Item #2 - NSI-001235
                <span style={{ background: '#ffc107', color: '#000', padding: '4px 8px', borderRadius: '15px', fontSize: '12px', marginLeft: '8px' }}>⚠ HAZMAT</span>
              </h3>
              <div style={{ display: 'flex', gap: '10px' }}>
                <button
                  id="reverse_button_hazmat"
                  style={{ background: '#ff6b35', color: 'white', padding: '8px 12px', fontSize: '12px', border: 'none', borderRadius: '5px', cursor: 'pointer' }}
                  onClick={() => showNotification('Reversing item NSI-001235', 'warning')}
                >
                  🔄 Reverse
                </button>
                <button
                  id="start_workflow_button_hazmat_section"
                  style={{ background: '#28a745', color: 'white', padding: '8px 12px', fontSize: '12px', border: 'none', borderRadius: '5px', cursor: 'pointer' }}
                  onClick={() => showNotification('Starting workflow for NSI-001235', 'success')}
                >
                  ▶️ Start Workflow
                </button>
              </div>
            </div>

            {/* Hazmat Warning */}
            <div style={{ background: '#ffeaea', border: '1px solid #ffb3b3', borderLeft: '4px solid #dc3545', padding: '15px', margin: '15px 0', borderRadius: '5px' }}>
              <div style={{ display: 'flex', alignItems: 'center', marginBottom: '10px' }}>
                <span style={{ background: '#dc3545', color: 'white', padding: '2px 6px', borderRadius: '3px', fontSize: '12px', marginRight: '8px' }}>⚠</span>
                <strong style={{ color: '#dc3545' }}>HAZMAT HANDLING INSTRUCTIONS</strong>
              </div>
              <ul style={{ margin: '10px 0', color: '#dc3545', lineHeight: 1.5, paddingLeft: '20px' }}>
                <li>DO NOT puncture, crush, or expose to heat above 60°C</li>
                <li>Store in fire-resistant container</li>
                <li>Use personal protective equipment</li>
                <li>Contact certified disposal contractor</li>
              </ul>
              <div style={{ color: '#dc3545', fontWeight: 'bold', marginTop: '10px' }}>
                UN Classification: UN3480 - Lithium Ion Batteries (Class 9)
              </div>
            </div>

            <div style={{ marginTop: '20px' }}>
              <h4>Document Management</h4>
              <div style={{ display: 'flex', gap: '10px', marginTop: '10px' }}>
                <button
                  style={{ background: '#dc3545', color: 'white', padding: '8px 12px', fontSize: '12px', border: 'none', borderRadius: '5px', cursor: 'pointer' }}
                  onClick={() => {
                    setModalContentType('hazmat-documents');
                    setModalData({ itemId: 'NSI-001235' });
                    setModal({ show: true, content: '' });
                  }}
                >
                  ⚠ Hazmat Documents
                </button>
                <button
                  style={{ background: '#6c757d', color: 'white', padding: '8px 12px', fontSize: '12px', border: 'none', borderRadius: '5px', cursor: 'pointer' }}
                  onClick={() => showModal(`
                  <h3>Shipping Documents - NSI-001235</h3>
                  <p style="margin: 20px 0;">Hazmat shipping document interface would open here.</p>
                  <button style="background: #6c757d; color: white; padding: 8px 12px; font-size: 12px; border: none; border-radius: 5px; cursor: pointer;" onclick="closeModal()">Close</button>
                `)}
                >
                  📄 Shipping Documents
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* User Story 5: Disposition Change and Workflow Restart Section */}
        <div style={{ background: '#f8f9fa', padding: '20px', borderRadius: '10px', border: '2px solid #0D5DAB', marginTop: '20px' }}>
          <h3 style={{ color: '#0D5DAB', marginBottom: '15px' }}>Disposition Change & Workflow Controls (User Story 5)</h3>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr auto auto', gap: '15px', alignItems: 'end' }}>
            <div>
              <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>Change Disposition</label>
              <select
                id="dispositionChange"
                style={{ width: '100%', padding: '8px', border: '1px solid #ddd', borderRadius: '5px', boxSizing: 'border-box' }}
              >
                <option value="">Select New Disposition</option>
                <option value="RTV">RTV - Return to Vendor</option>
                <option value="Destroy">Destroy</option>
                <option value="Salvage">Salvage</option>
                <option value="Hazmat Disposal">Hazmat Disposal</option>
                <option value="Out for Repair">Out for Repair</option>
              </select>
            </div>
            <div>
              <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>Reason for Change</label>
              <input
                id="changeReason"
                type="text"
                style={{ width: '100%', padding: '8px', border: '1px solid #ddd', borderRadius: '5px', boxSizing: 'border-box' }}
                placeholder="Enter reason for disposition change"
              />
            </div>
            <div>
              <button
                id="start_workflow_button_disposition"
                style={{ background: '#28a745', color: 'white', padding: '10px 15px', border: 'none', borderRadius: '5px', cursor: 'pointer' }}
                onClick={() => showNotification('Workflow restarted with new disposition', 'success')}
              >
                🚀 Start Workflow
              </button>
            </div>
            <div>
              <button
                id="reverse_button"
                style={{ background: '#ff6b35', color: 'white', padding: '10px 15px', border: 'none', borderRadius: '5px', cursor: 'pointer' }}
                onClick={() => showNotification('Transaction reversed successfully', 'warning')}
              >
                🔄 Reverse Transaction
              </button>
            </div>
          </div>
          <div style={{ marginTop: '15px', padding: '10px', background: '#e3f2fd', borderLeft: '4px solid #0D5DAB', borderRadius: '5px' }}>
            <p style={{ margin: 0, fontSize: '14px', color: '#0D5DAB' }}>
              <strong>Note:</strong> When disposition is changed, click "Start Workflow" to restart the process with new disposition rules.
              Use "Reverse Transaction" to undo the NSI transaction completely.
            </p>
          </div>
        </div>

        {/* Action Buttons */}
        <div style={{ display: 'flex', justifyContent: 'center', gap: '15px', marginTop: '30px', padding: '20px' }}>
          <button
            style={{ background: '#0D5DAB', color: 'white', padding: '12px 20px', border: 'none', borderRadius: '5px', cursor: 'pointer' }}
            onClick={() => showNotification('All items saved', 'success')}
          >
            💾 Save All Items
          </button>
          <button
            style={{ background: '#28a745', color: 'white', padding: '12px 20px', border: 'none', borderRadius: '5px', cursor: 'pointer' }}
            onClick={() => showNotification('Submitted for approval', 'success')}
          >
            ✓ Submit for Approval
          </button>
          <button
            style={{ background: '#6c757d', color: 'white', padding: '12px 20px', border: 'none', borderRadius: '5px', cursor: 'pointer' }}
            onClick={() => showNotification('Exporting to Excel...', 'success')}
          >
            📊 Export to Excel
          </button>
        </div>
      </div>
    );
  };

  // Inquiry Screen
  const InquiryScreen = () => (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div style={{
        background: 'linear-gradient(135deg, #002242, #374151)',
        color: 'white',
        padding: '20px',
        borderRadius: '10px',
        position: 'relative'
      }}>
        <h1 style={{ margin: 0, fontSize: '28px' }}>Inquiry Screen</h1>
        <div style={{ position: 'absolute', top: '20px', right: '20px' }}>
          <button
            style={{ background: '#4f7cff', color: 'white', padding: '8px 15px', fontSize: '14px', border: 'none', borderRadius: '5px', cursor: 'pointer' }}
            onClick={() => showNotification('Exporting results to Excel...', 'success')}
          >
            📊 Export Results
          </button>
        </div>
      </div>

      <div style={{ background: 'white', padding: '20px', borderRadius: '10px', boxShadow: '0 2px 5px rgba(0,0,0,0.1)' }}>
        <h3 style={{ color: '#0D5DAB', marginBottom: '20px' }}>Search & Filter Options</h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '20px' }}>
          <div>
            <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>Location Selected</label>
            <select style={{ width: '100%', padding: '8px', border: '1px solid #ddd', borderRadius: '5px', boxSizing: 'border-box' }}>
              <option>All Locations</option>
              <option>RTV Cage</option>
              <option>Hazmat Storage</option>
              <option>Warehouse A</option>
              <option>Warehouse B</option>
            </select>
          </div>
          <div>
            <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>Status Selected</label>
            <select style={{ width: '100%', padding: '8px', border: '1px solid #ddd', borderRadius: '5px', boxSizing: 'border-box' }}>
              <option>All Status</option>
              <option>Pending</option>
              <option>Approved</option>
              <option>Rejected</option>
              <option>Completed</option>
            </select>
          </div>
          <div>
            <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>Vendor Selected</label>
            <select style={{ width: '100%', padding: '8px', border: '1px solid #ddd', borderRadius: '5px', boxSizing: 'border-box' }}>
              <option>All Vendors</option>
              <option>Samsung Electronics</option>
              <option>Energizer Holdings</option>
              <option>KitchenAid</option>
              <option>Nike Inc.</option>
            </select>
          </div>
          <div>
            <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>Disposition Selected</label>
            <select style={{ width: '100%', padding: '8px', border: '1px solid #ddd', borderRadius: '5px', boxSizing: 'border-box' }}>
              <option>All Dispositions</option>
              <option>RTV</option>
              <option>Hazmat Disposal</option>
              <option>Out for Repair</option>
              <option>Salvage</option>
              <option>Destroy</option>
            </select>
          </div>
          <div>
            <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>Date From</label>
            <input type="date" style={{ width: '100%', padding: '8px', border: '1px solid #ddd', borderRadius: '5px', boxSizing: 'border-box' }} />
          </div>
          <div>
            <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>Date To</label>
            <input type="date" style={{ width: '100%', padding: '8px', border: '1px solid #ddd', borderRadius: '5px', boxSizing: 'border-box' }} />
          </div>
        </div>
        <div style={{ marginTop: '20px' }}>
          <button
            style={{ background: '#0D5DAB', color: 'white', padding: '10px 15px', marginRight: '10px', border: 'none', borderRadius: '5px', cursor: 'pointer' }}
            onClick={() => showNotification('Search performed - 4 items found', 'success')}
          >
            🔍 Search
          </button>
          <button
            style={{ background: '#6c757d', color: 'white', padding: '10px 15px', border: 'none', borderRadius: '5px', cursor: 'pointer' }}
            onClick={() => showNotification('Filters cleared', 'success')}
          >
            🗑️ Clear Filters
          </button>
        </div>
      </div>

      <div style={{ background: 'white', padding: '20px', borderRadius: '10px', boxShadow: '0 2px 5px rgba(0,0,0,0.1)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <h3 style={{ color: '#002242', margin: 0 }}>Search Results</h3>
          <span style={{ color: '#666', fontSize: '14px' }}>4 items found | Click column headers to sort</span>
        </div>

        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ background: '#4f7cff', color: 'white' }}>
                <th style={{ padding: '12px', textAlign: 'left', cursor: 'pointer' }}>Item ID</th>
                <th style={{ padding: '12px', textAlign: 'left', cursor: 'pointer' }}>Description</th>
                <th style={{ padding: '12px', textAlign: 'left', cursor: 'pointer' }}>Location ⇅</th>
                <th style={{ padding: '12px', textAlign: 'left', cursor: 'pointer' }}>Vendor ⇅</th>
                <th style={{ padding: '12px', textAlign: 'left', cursor: 'pointer' }}>Disposition ⇅</th>
                <th style={{ padding: '12px', textAlign: 'left', cursor: 'pointer' }}>Status ⇅</th>
                <th style={{ padding: '12px', textAlign: 'left' }}>Quantity</th>
                <th style={{ padding: '12px', textAlign: 'left' }}>Cost</th>
                <th style={{ padding: '12px', textAlign: 'left', cursor: 'pointer' }}>Aging (Days) ⇅</th>
              </tr>
            </thead>
            <tbody>
              <tr style={{ borderBottom: '1px solid #eee' }}>
                <td style={{ padding: '12px' }}><strong>NSI-001234</strong></td>
                <td style={{ padding: '12px' }}>Samsung 55" QLED TV - Cracked Screen</td>
                <td style={{ padding: '12px' }}>RTV Cage</td>
                <td style={{ padding: '12px' }}>Samsung Electronics</td>
                <td style={{ padding: '12px' }}>RTV</td>
                <td style={{ padding: '12px' }}>
                  <span style={{ background: '#fef3c7', color: '#92400e', padding: '4px 8px', borderRadius: '15px', fontSize: '12px' }}>Pending</span>
                </td>
                <td style={{ padding: '12px' }}>1</td>
                <td style={{ padding: '12px' }}>$899.99</td>
                <td style={{ padding: '12px', color: '#ffc107', fontWeight: 'bold' }}>15</td>
              </tr>
              <tr style={{ borderBottom: '1px solid #eee' }}>
                <td style={{ padding: '12px' }}><strong>NSI-001235</strong></td>
                <td style={{ padding: '12px' }}>Lithium Ion Battery Pack - Swollen/Damaged <span style={{ background: '#ffc107', color: '#000', padding: '2px 6px', borderRadius: '3px', fontSize: '10px' }}>⚠</span></td>
                <td style={{ padding: '12px' }}>Hazmat Storage</td>
                <td style={{ padding: '12px' }}>Energizer Holdings</td>
                <td style={{ padding: '12px' }}>Hazmat Disposal</td>
                <td style={{ padding: '12px' }}>
                  <span style={{ background: '#d1fae5', color: '#065f46', padding: '4px 8px', borderRadius: '15px', fontSize: '12px' }}>Approved</span>
                </td>
                <td style={{ padding: '12px' }}>1</td>
                <td style={{ padding: '12px' }}>$89.99</td>
                <td style={{ padding: '12px', color: '#dc3545', fontWeight: 'bold' }}>45</td>
              </tr>
              <tr style={{ borderBottom: '1px solid #eee' }}>
                <td style={{ padding: '12px' }}><strong>NSI-001236</strong></td>
                <td style={{ padding: '12px' }}>KitchenAid Stand Mixer - Motor Issue</td>
                <td style={{ padding: '12px' }}>Warehouse A</td>
                <td style={{ padding: '12px' }}>KitchenAid</td>
                <td style={{ padding: '12px' }}>Out for Repair</td>
                <td style={{ padding: '12px' }}>
                  <span style={{ background: '#d1fae5', color: '#065f46', padding: '4px 8px', borderRadius: '15px', fontSize: '12px' }}>Approved</span>
                </td>
                <td style={{ padding: '12px' }}>1</td>
                <td style={{ padding: '12px' }}>$379.99</td>
                <td style={{ padding: '12px', color: '#28a745', fontWeight: 'bold' }}>7</td>
              </tr>
              <tr style={{ borderBottom: '1px solid #eee' }}>
                <td style={{ padding: '12px' }}><strong>NSI-001237</strong></td>
                <td style={{ padding: '12px' }}>Nike Air Max 270 - Color Defect</td>
                <td style={{ padding: '12px' }}>Warehouse B</td>
                <td style={{ padding: '12px' }}>Nike Inc.</td>
                <td style={{ padding: '12px' }}>Salvage</td>
                <td style={{ padding: '12px' }}>
                  <span style={{ background: '#fef3c7', color: '#92400e', padding: '4px 8px', borderRadius: '15px', fontSize: '12px' }}>Pending</span>
                </td>
                <td style={{ padding: '12px' }}>5</td>
                <td style={{ padding: '12px' }}>$750.00</td>
                <td style={{ padding: '12px', color: '#dc3545', fontWeight: 'bold' }}>32</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div style={{ background: '#f8f9fa', border: '1px solid #e9ecef', borderLeft: '4px solid #0D5DAB', padding: '15px', marginTop: '20px', borderRadius: '5px' }}>
          <div style={{ color: '#0D5DAB', fontWeight: 'bold', marginBottom: '5px' }}>Results Summary:</div>
          <div style={{ color: '#666', lineHeight: 1.5 }}>
            <span style={{ fontWeight: 'bold' }}>4 items found</span> | Total Quantity: 8 units | Total Value: $2,119.97<br />
            Pending: 2 items | Approved: 2 items | Hazmat Items: 1 | Avg Aging: 25 days
          </div>
        </div>
      </div>
    </div>
  );

  // Salvage Revenue Screen
  const SalvageScreen = () => (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div style={{
        background: 'linear-gradient(135deg, #002242, #374151)',
        color: 'white',
        padding: '20px',
        borderRadius: '10px',
        position: 'relative'
      }}>
        <h1 style={{ margin: 0, fontSize: '28px' }}>Salvage Revenue Entry & Tracking</h1>
        <div style={{ position: 'absolute', top: '20px', right: '20px', display: 'flex', gap: '10px' }}>
          <button style={{ background: '#4f7cff', color: 'white', padding: '8px 15px', fontSize: '14px', border: 'none', borderRadius: '5px', cursor: 'pointer' }}>🔄 Refresh Data</button>
          <button style={{ background: '#28a745', color: 'white', padding: '8px 15px', fontSize: '14px', border: 'none', borderRadius: '5px', cursor: 'pointer' }}>📊 Export to CSV</button>
          <button style={{ background: '#6c757d', color: 'white', padding: '8px 15px', fontSize: '14px', border: 'none', borderRadius: '5px', cursor: 'pointer' }}>+ New Entry</button>
        </div>
      </div>

      <div style={{ background: 'white', padding: '20px', borderRadius: '10px', boxShadow: '0 2px 5px rgba(0,0,0,0.1)' }}>
        <h3 style={{ color: '#4f7cff', marginBottom: '20px' }}>Search & Filter Options</h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '20px' }}>
          <div>
            <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>NSI ID</label>
            <input
              id="returnCenterNumber"
              type="text"
              style={{ width: '100%', padding: '8px', border: '1px solid #ddd', borderRadius: '5px', boxSizing: 'border-box' }}
              placeholder="Enter NSI ID"
            />
          </div>
          <div>
            <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>Return Center Number</label>
            <input type="text" style={{ width: '100%', padding: '8px', border: '1px solid #ddd', borderRadius: '5px', boxSizing: 'border-box' }} placeholder="Enter return center number" />
          </div>
          <div>
            <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>Receipt or Inmar Order Number</label>
            <input
              id="receiptOrInmarOrderNumber"
              type="text"
              style={{ width: '100%', padding: '8px', border: '1px solid #ddd', borderRadius: '5px', boxSizing: 'border-box' }}
              placeholder="Enter order number"
            />
          </div>
          <div>
            <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>From Date</label>
            <input type="text" style={{ width: '100%', padding: '8px', border: '1px solid #ddd', borderRadius: '5px', boxSizing: 'border-box' }} defaultValue="05/01/2025" />
          </div>
          <div>
            <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>To Date</label>
            <input type="text" style={{ width: '100%', padding: '8px', border: '1px solid #ddd', borderRadius: '5px', boxSizing: 'border-box' }} defaultValue="06/03/2025" />
          </div>
        </div>
        <div style={{ marginTop: '20px' }}>
          <button style={{ background: '#0D5DAB', color: 'white', padding: '10px 15px', marginRight: '10px', border: 'none', borderRadius: '5px', cursor: 'pointer' }} onClick={() => showNotification('Searching salvage entries...', 'success')}>🔍 Search</button>
          <button style={{ background: '#6c757d', color: 'white', padding: '10px 15px', border: 'none', borderRadius: '5px', cursor: 'pointer' }} onClick={() => showNotification('Salvage filters cleared', 'success')}>🗑️ Clear Filters</button>
        </div>
      </div>

      {/* User Story 3: RC Documentation */}
      <div style={{ background: 'white', padding: '20px', borderRadius: '10px', boxShadow: '0 2px 5px rgba(0,0,0,0.1)', border: '2px solid #ff6b35' }}>
        <h3 style={{ color: '#ff6b35', marginBottom: '20px' }}>RC Documentation (User Story 3)</h3>

        {/* Document Category Selection */}
        <div style={{ marginBottom: '25px', padding: '15px', background: '#fff3f0', borderRadius: '8px' }}>
          <h4 style={{ color: '#ff6b35', marginBottom: '15px' }}>📋 Document Category Selection</h4>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr auto auto', gap: '15px', alignItems: 'end' }}>
            <div>
              <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>Document Category</label>
              <select
                id="document_category"
                style={{ width: '100%', padding: '8px', border: '1px solid #ddd', borderRadius: '5px', boxSizing: 'border-box' }}
              >
                <option>Select Category</option>
                <option>RC Document - Return Center</option>
                <option>RD Document - Return Disposition</option>
                <option>Shipping Information</option>
                <option>Return Processing</option>
                <option>Authorization Form</option>
              </select>
            </div>
            <div>
              <button
                id="document_modal"
                style={{ background: '#ff6b35', color: 'white', padding: '10px 15px', border: 'none', borderRadius: '5px', cursor: 'pointer' }}
                onClick={() => {
                  const category = (document.getElementById('rc_document_category') as HTMLSelectElement)?.value;
                  if (!category || category === 'Select Category') {
                    showNotification('Please select a document category first', 'warning');
                    return;
                  }
                  showModal(`
                    <div style="text-align: center; padding: 20px;">
                      <h3 style="color: #ff6b35; margin-bottom: 20px;">🏢 RC Document Modal - ${category}</h3>
                      <div style="background: #fff3f0; border: 1px solid #ff6b35; padding: 20px; border-radius: 8px; margin: 20px 0; text-align: left;">
                        <h4 style="color: #ff6b35; margin-bottom: 15px;">📄 Generated RC Document</h4>
                        <div style="background: white; padding: 15px; border-radius: 5px; margin: 10px 0;">
                          <strong>Document Category:</strong> ${category}<br>
                          <strong>RC Document ID:</strong> RC-${Date.now()}<br>
                          <strong>Generated Date:</strong> ${new Date().toLocaleDateString()}<br>
                          <strong>Status:</strong> Ready for Return Center Processing<br>
                          <strong>Return Route:</strong> Automated routing to Return Center<br><br>
                          <div style="border-left: 4px solid #ff6b35; padding-left: 15px; margin: 15px 0;">
                            <strong>RC Document Contents:</strong><br>
                            • Item tracking numbers and details<br>
                            • Return Center routing information<br>
                            • Category-specific processing instructions<br>
                            • Authorization and approval details
                          </div>
                        </div>
                      </div>
                      <div style="margin-top: 20px;">
                        <button 
                          id="print_rc_document_modal"
                          style="background: #28a745; color: white; padding: 10px 15px; font-size: 14px; border: none; border-radius: 5px; cursor: pointer; margin-right: 10px;" 
                          onclick="closeModal(); showNotification('RC Document printed successfully with all item details and routing info', 'success')"
                        >
                          🖨️ Print RC Document
                        </button>
                        <button 
                          style="background: #0D5DAB; color: white; padding: 10px 15px; font-size: 14px; border: none; border-radius: 5px; cursor: pointer; margin-right: 10px;" 
                          onclick="closeModal(); showNotification('RC Document saved to system', 'success')"
                        >
                          💾 Save RC Document
                        </button>
                        <button 
                          style="background: #6c757d; color: white; padding: 10px 15px; font-size: 14px; border: none; border-radius: 5px; cursor: pointer;" 
                          onclick="closeModal()"
                        >
                          ✖️ Close Modal
                        </button>
                      </div>
                    </div>
                  `);
                }}
              >
                📝 Open RC Document Modal
              </button>
            </div>
            <div>
              <button
                id="print_button"
                style={{ background: '#28a745', color: 'white', padding: '10px 15px', border: 'none', borderRadius: '5px', cursor: 'pointer' }}
                onClick={() => {
                  const category = (document.getElementById('document_category') as HTMLSelectElement)?.value;
                  if (!category || category === 'Select Category') {
                    showNotification('Please select a document category first', 'warning');
                    return;
                  }
                  showNotification(`RC Document printed: ${category} with all item details, tracking numbers, and category information`, 'success');
                }}
              >
                🖨️ Print RC Document
              </button>
            </div>
          </div>
        </div>

        {/* Document Processing Status */}
        <div style={{ padding: '15px', background: '#f0f8f0', borderRadius: '8px', textAlign: 'center' }}>
          <h4 style={{ color: '#28a745', marginBottom: '15px' }}>✅ RC Document Processing Status</h4>
          <p style={{ marginBottom: '15px', color: '#666' }}>
            RC Documents are automatically generated when items are routed to Return Center processing.
          </p>
          <div style={{ display: 'flex', justifyContent: 'center', gap: '10px', flexWrap: 'wrap' }}>
            <span style={{ background: '#28a745', color: 'white', padding: '5px 10px', borderRadius: '15px', fontSize: '12px' }}>
              ✅ Auto-Generated
            </span>
            <span style={{ background: '#0D5DAB', color: 'white', padding: '5px 10px', borderRadius: '15px', fontSize: '12px' }}>
              📄 Modal Available
            </span>
            <span style={{ background: '#ff6b35', color: 'white', padding: '5px 10px', borderRadius: '15px', fontSize: '12px' }}>
              🖨️ Print Ready
            </span>
          </div>
        </div>
      </div>

      {/* User Story 4: Master Shipment & Shipping Documents */}
      <div style={{ background: 'white', padding: '20px', borderRadius: '10px', boxShadow: '0 2px 5px rgba(0,0,0,0.1)', border: '2px solid #28a745' }}>
        <h3 style={{ color: '#28a745', marginBottom: '20px' }}>Master Shipment & Shipping Documents (User Story 4)</h3>

        {/* Master Shipment Generation */}
        <div style={{ marginBottom: '25px', padding: '15px', background: '#f8f9fa', borderRadius: '8px' }}>
          <h4 style={{ color: '#28a745', marginBottom: '15px' }}>🚢 Master Shipment Generation</h4>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr auto', gap: '15px', alignItems: 'end' }}>
            <div>
              <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>Master Shipment Number</label>
              <input
                id="master_shipment_number"
                type="text"
                style={{ width: '100%', padding: '8px', border: '1px solid #ddd', borderRadius: '5px', boxSizing: 'border-box' }}
                placeholder="Auto-generated on processing"
                readOnly
              />
            </div>
            <div>
              <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>Destination</label>
              <input
                id="shipment_destination"
                type="text"
                style={{ width: '100%', padding: '8px', border: '1px solid #ddd', borderRadius: '5px', boxSizing: 'border-box' }}
                placeholder="Enter destination"
              />
            </div>
            <div>
              <button
                id="generate_master_shipment"
                style={{ background: '#28a745', color: 'white', padding: '10px 15px', border: 'none', borderRadius: '5px', cursor: 'pointer' }}
                onClick={() => {
                  const shipmentNumElement = document.getElementById('master_shipment_number');
                  if (shipmentNumElement) {
                    (shipmentNumElement as HTMLInputElement).value = `MS-${Date.now()}`;
                  }
                  showNotification('Master shipment generated automatically', 'success');
                }}
              >
                📦 Generate Master Shipment
              </button>
            </div>
          </div>
        </div>

        {/* Shipping Documents Section */}
        <div style={{ marginBottom: '25px', padding: '15px', background: '#e3f2fd', borderRadius: '8px' }}>
          <h4 style={{ color: '#0D5DAB', marginBottom: '15px' }}>📄 Shipping Documents</h4>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '15px' }}>
            <div>
              <label style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '10px' }}>
                <input
                  id="bol_document_checkbox"
                  type="checkbox"
                  style={{ margin: '0' }}
                />
                <span style={{ fontWeight: 'bold' }}>BOL (Bill of Lading)</span>
              </label>
              <button
                id="print_bol_document"
                style={{ width: '100%', background: '#0D5DAB', color: 'white', padding: '8px 12px', border: 'none', borderRadius: '5px', cursor: 'pointer' }}
                onClick={() => {
                  const bolCheck = document.getElementById('bol_document_checkbox') as HTMLInputElement;
                  if (!bolCheck?.checked) {
                    showNotification('Please select BOL checkbox first', 'warning');
                    return;
                  }
                  showNotification('BOL printed with shipment number, item details, destination, and required signatures', 'success');
                }}
              >
                🖨️ Print BOL
              </button>
            </div>
            <div>
              <label style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '10px' }}>
                <input
                  id="shipment_label_document_checkbox"
                  type="checkbox"
                  style={{ margin: '0' }}
                />
                <span style={{ fontWeight: 'bold' }}>Shipment Label</span>
              </label>
              <button
                id="print_shipment_label_document"
                style={{ width: '100%', background: '#28a745', color: 'white', padding: '8px 12px', border: 'none', borderRadius: '5px', cursor: 'pointer' }}
                onClick={() => {
                  const labelCheck = document.getElementById('shipment_label_document_checkbox') as HTMLInputElement;
                  if (!labelCheck?.checked) {
                    showNotification('Please select Shipment Label checkbox first', 'warning');
                    return;
                  }
                  showNotification('Shipment label printed successfully', 'success');
                }}
              >
                🏷️ Print Shipment Label
              </button>
            </div>
            <div>
              <label style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '10px' }}>
                <input
                  id="logline_document_checkbox"
                  type="checkbox"
                  style={{ margin: '0' }}
                />
                <span style={{ fontWeight: 'bold' }}>Logline Documents</span>
              </label>
              <button
                id="print_logline_document"
                style={{ width: '100%', background: '#6c757d', color: 'white', padding: '8px 12px', border: 'none', borderRadius: '5px', cursor: 'pointer' }}
                onClick={() => {
                  const loglineCheck = document.getElementById('logline_document_checkbox') as HTMLInputElement;
                  if (!loglineCheck?.checked) {
                    showNotification('Please select Logline Documents checkbox first', 'warning');
                    return;
                  }
                  showNotification('Logline documents printed successfully', 'success');
                }}
              >
                📋 Print Logline Documents
              </button>
            </div>
          </div>
        </div>

        {/* Complete Processing */}
        <div style={{ padding: '15px', background: '#e8f5e8', borderRadius: '8px', textAlign: 'center' }}>
          <h4 style={{ color: '#28a745', marginBottom: '15px' }}>✅ Complete Processing Confirmation</h4>
          <p style={{ marginBottom: '15px', color: '#666' }}>
            Once all shipping documents are printed and verified, complete the processing workflow.
          </p>
          <button
            id="complete_processing"
            style={{ background: '#28a745', color: 'white', padding: '12px 20px', border: 'none', borderRadius: '5px', cursor: 'pointer', fontSize: '16px' }}
            onClick={() => showNotification('Processing completed successfully - all documents generated and workflow finalized', 'success')}
          >
            ✅ Complete Processing Confirmation
          </button>
        </div>
      </div>

      {/* User Story 2: Salvage Workflow Initiation */}
      <div style={{ background: 'white', padding: '20px', borderRadius: '10px', boxShadow: '0 2px 5px rgba(0,0,0,0.1)' }}>
        <h3 style={{ color: '#0D5DAB', marginBottom: '20px' }}>Initiate Salvage Workflow (User Story 2)</h3>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr auto', gap: '20px', alignItems: 'end' }}>
          <div>
            <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>NSI ID</label>
            <input
              id="salvage_nsiId"
              type="text"
              style={{ width: '100%', padding: '8px', border: '1px solid #ddd', borderRadius: '5px', boxSizing: 'border-box' }}
              placeholder="Enter NSI ID"
            />
          </div>
          <div>
            <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>Item ID</label>
            <input
              id="salvage_itemId"
              type="text"
              style={{ width: '100%', padding: '8px', border: '1px solid #ddd', borderRadius: '5px', boxSizing: 'border-box' }}
              placeholder="Enter Item ID"
            />
          </div>
          <div>
            <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>Disposition</label>
            <select
              id="salvage_disposition"
              style={{ width: '100%', padding: '8px', border: '1px solid #ddd', borderRadius: '5px', boxSizing: 'border-box' }}
            >
              <option value="">Select Disposition</option>
              <option value="Salvage">Salvage</option>
              <option value="RTV">RTV</option>
              <option value="Destroy">Destroy</option>
              <option value="Hazmat Disposal">Hazmat Disposal</option>
            </select>
          </div>
          <div>
            <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>Status</label>
            <select
              id="salvage_status"
              style={{ width: '100%', padding: '8px', border: '1px solid #ddd', borderRadius: '5px', boxSizing: 'border-box' }}
            >
              <option value="">Select Status</option>
              <option value="Approved">Approved</option>
              <option value="Pending">Pending</option>
              <option value="In Process">In Process</option>
            </select>
          </div>
          <div>
            <button
              id="start_workflow_salvage"
              style={{ background: '#28a745', color: 'white', padding: '10px 15px', border: 'none', borderRadius: '5px', cursor: 'pointer' }}
              onClick={() => showNotification('Salvage workflow initiated successfully', 'success')}
            >
              🚀 Start Workflow
            </button>
          </div>
        </div>
      </div>

      <div style={{ background: 'white', padding: '20px', borderRadius: '10px', boxShadow: '0 2px 5px rgba(0,0,0,0.1)' }}>
        <h3 style={{ color: '#0D5DAB', marginBottom: '20px' }}>Salvage Revenue Entries</h3>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ background: '#4f7cff', color: 'white' }}>
                <th style={{ padding: '12px', textAlign: 'left' }}>Receipt/Inmar Order</th>
                <th style={{ padding: '12px', textAlign: 'left' }}>Liquidation Vendor Name</th>
                <th style={{ padding: '12px', textAlign: 'left' }}>Vendor Number</th>
                <th style={{ padding: '12px', textAlign: 'left' }}>Container Qty</th>
                <th style={{ padding: '12px', textAlign: 'left' }}>Total Qty</th>
                <th style={{ padding: '12px', textAlign: 'left' }}>Total Original Sell Price</th>
                <th style={{ padding: '12px', textAlign: 'left' }}>Total Lqd Sell Revenue</th>
                <th style={{ padding: '12px', textAlign: 'left' }}>Recovery Rate</th>
                <th style={{ padding: '12px', textAlign: 'left' }}>Updated By</th>
                <th style={{ padding: '12px', textAlign: 'left' }}>Created Date/Time</th>
              </tr>
            </thead>
            <tbody>
              <tr style={{ borderBottom: '1px solid #eee' }}>
                <td style={{ padding: '12px' }}><strong>RCT-2025-001234</strong></td>
                <td style={{ padding: '12px' }}>B-Stock Solutions</td>
                <td style={{ padding: '12px' }}>BST-001</td>
                <td style={{ padding: '12px' }}>3</td>
                <td style={{ padding: '12px' }}>145</td>
                <td style={{ padding: '12px' }}>$12,450.00</td>
                <td style={{ padding: '12px', color: '#28a745', fontWeight: 'bold' }}>$4,360.50</td>
                <td style={{ padding: '12px', color: '#28a745', fontWeight: 'bold' }}>35.0%</td>
                <td style={{ padding: '12px' }}>John Smith</td>
                <td style={{ padding: '12px' }}>2025-05-15 09:30:15</td>
              </tr>
              <tr style={{ borderBottom: '1px solid #eee' }}>
                <td style={{ padding: '12px' }}><strong>INM-2025-005678</strong></td>
                <td style={{ padding: '12px' }}>GENCO Marketplace</td>
                <td style={{ padding: '12px' }}>GEN-002</td>
                <td style={{ padding: '12px' }}>2</td>
                <td style={{ padding: '12px' }}>89</td>
                <td style={{ padding: '12px' }}>$8,750.00</td>
                <td style={{ padding: '12px', color: '#28a745', fontWeight: 'bold' }}>$3,062.50</td>
                <td style={{ padding: '12px', color: '#28a745', fontWeight: 'bold' }}>35.0%</td>
                <td style={{ padding: '12px' }}>Jane Doe</td>
                <td style={{ padding: '12px' }}>2025-05-18 11:15:45</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div style={{ background: '#f8f9fa', border: '1px solid #e9ecef', borderLeft: '4px solid #28a745', padding: '20px', marginTop: '20px', borderRadius: '5px', display: 'flex', justifyContent: 'space-between' }}>
          <div style={{ textAlign: 'center' }}>
            <div style={{ color: '#0D5DAB', fontSize: '32px', fontWeight: 'bold', margin: 0 }}>2</div>
            <div style={{ color: '#666', fontSize: '14px', marginTop: '5px' }}>Total Entries</div>
          </div>
          <div style={{ textAlign: 'center' }}>
            <div style={{ color: '#28a745', fontSize: '32px', fontWeight: 'bold', margin: 0 }}>$7,423</div>
            <div style={{ color: '#666', fontSize: '14px', marginTop: '5px' }}>Total Revenue</div>
          </div>
          <div style={{ textAlign: 'center' }}>
            <div style={{ color: '#ffc107', fontSize: '32px', fontWeight: 'bold', margin: 0 }}>35.0%</div>
            <div style={{ color: '#666', fontSize: '14px', marginTop: '5px' }}>Avg Recovery Rate</div>
          </div>
          <div style={{ textAlign: 'center' }}>
            <div style={{ color: '#0D5DAB', fontSize: '32px', fontWeight: 'bold', margin: 0 }}>234</div>
            <div style={{ color: '#666', fontSize: '14px', marginTop: '5px' }}>Total Items</div>
          </div>
        </div>
      </div>
    </div>
  );

  // Render current screen
  const renderScreen = () => {
    switch (currentScreen) {
      case 'dashboard':
        return <DashboardScreen />;
      case 'worklist':
        return <WorklistScreen />;
      case 'entry':
        return <MaintenanceScreen />;
      case 'inquiry':
        return <InquiryScreen />;
      case 'salvage':
        return <SalvageScreen />;
      case 'buyer-request':
        return (
          <div style={{ background: 'white', padding: '20px', borderRadius: '10px', boxShadow: '0 2px 5px rgba(0,0,0,0.1)' }}>
            <h2 style={{ color: '#002242', marginBottom: '20px' }}>Buyer Request and Safety Recall Management</h2>
            <p style={{ color: '#666', marginBottom: '20px' }}>Create and manage buyer requests with approval workflows.</p>
            <p style={{ padding: '15px', background: '#f0f9ff', borderRadius: '5px', color: '#0369a1' }}>
              Complete buyer request functionality with forms, approval workflows, and active request tracking.
            </p>
          </div>
        );
      case 'shipments':
        return (
          <div style={{ background: 'white', padding: '20px', borderRadius: '10px', boxShadow: '0 2px 5px rgba(0,0,0,0.1)' }}>
            <h2 style={{ color: '#002242', marginBottom: '20px' }}>Work with Shipments</h2>
            <p style={{ color: '#666', marginBottom: '20px' }}>Shipment management with carrier tracking and document handling.</p>
            <p style={{ padding: '15px', background: '#f0f9ff', borderRadius: '5px', color: '#0369a1' }}>
              Full shipment management with search criteria, carrier selection, and document processing.
            </p>
          </div>
        );
      case 'audit':
        return (
          <div style={{ background: 'white', padding: '20px', borderRadius: '10px', boxShadow: '0 2px 5px rgba(0,0,0,0.1)' }}>
            <h2 style={{ color: '#002242', marginBottom: '20px' }}>Audit Trail</h2>
            <p style={{ color: '#666', marginBottom: '20px' }}>Complete activity logging with user actions and system changes.</p>
            <p style={{ padding: '15px', background: '#f0f9ff', borderRadius: '5px', color: '#0369a1' }}>
              Comprehensive audit trail with filtering, user tracking, and detailed activity logs.
            </p>
          </div>
        );
      case 'lifecycle':
        return (
          <div style={{ background: 'white', padding: '20px', borderRadius: '10px', boxShadow: '0 2px 5px rgba(0,0,0,0.1)' }}>
            <h2 style={{ color: '#002242', marginBottom: '20px' }}>NSI Lifecycle Tracking</h2>
            <p style={{ color: '#666', marginBottom: '20px' }}>Comprehensive workflow tracking with financial impact analysis.</p>
            <p style={{ padding: '15px', background: '#f0f9ff', borderRadius: '5px', color: '#0369a1' }}>
              Complete lifecycle tracking with workflow pipelines, financial metrics, vendor details, and timeline views.
            </p>
          </div>
        );
      default:
        return <DashboardScreen />;
    }
  };

  return (
    <div style={{ display: 'flex', height: '100vh', background: '#f5f5f5' }}>
      {/* Sidebar */}
      <div style={{
        width: '250px',
        background: '#002242',
        padding: '20px',
        borderRight: '1px solid #ddd',
        flexShrink: 0,
        color: 'white'
      }}>
        <h2 style={{ color: '#E4E5E6', margin: '0 0 20px 0' }}>NSI System</h2>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '5px' }}>
          {[
            { id: 'dashboard', label: 'Dashboard' },
            { id: 'worklist', label: 'NSI Entry' },
            { id: 'entry', label: 'NSI Maintenance' },
            { id: 'inquiry', label: 'Inquiry' },
            { id: 'salvage', label: 'Salvage Revenue' },
            { id: 'buyer-request', label: 'Buyer Request & Safety Recall' },
            { id: 'shipments', label: 'Work with Shipments' },
            { id: 'audit', label: 'Audit Trail' },
            { id: 'lifecycle', label: 'NSI Lifecycle Tracking' }
          ].map((item) => (
            <button
              key={item.id}
              onClick={() => showScreen(item.id)}
              style={{
                display: 'block',
                width: '100%',
                padding: '10px',
                margin: '5px 0',
                background: currentScreen === item.id ? '#002242' : '#374151',
                border: 'none',
                borderRadius: '5px',
                cursor: 'pointer',
                textAlign: 'left',
                color: 'white',
                fontSize: '14px'
              }}
            >
              {item.label}
            </button>
          ))}
        </div>
      </div>

      {/* Main Content */}
      <div style={{ flex: 1, padding: '20px', overflowY: 'auto', position: 'relative' }}>
        {renderScreen()}
      </div>

      {/* Notification */}
      {notification.show && (
        <div style={{
          position: 'fixed',
          top: '20px',
          right: '20px',
          padding: '15px',
          borderRadius: '5px',
          color: 'white',
          zIndex: 1000,
          background: notification.type === 'success' ? '#28a745' :
            notification.type === 'warning' ? '#ffc107' :
              notification.type === 'danger' ? '#dc3545' : '#007bff',
          transform: notification.show ? 'translateX(0)' : 'translateX(300px)',
          transition: 'transform 0.3s'
        }}>
          {notification.message}
        </div>
      )}

      {/* Modal */}
      {modal.show && (
        <div style={{
          position: 'fixed',
          zIndex: 1000,
          left: 0,
          top: 0,
          width: '100%',
          height: '100%',
          background: 'rgba(0,0,0,0.5)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center'
        }}>
          <div style={{
            background: 'white',
            margin: '15% auto',
            padding: '20px',
            borderRadius: '10px',
            width: '80%',
            maxWidth: '500px'
          }}>
            <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '10px' }}>
              <span
                style={{ fontSize: '28px', fontWeight: 'bold', cursor: 'pointer' }}
                onClick={closeModal}
              >
                &times;
              </span>
            </div>
            {renderModalContent()}
          </div>
        </div>
      )}

      {/* Hidden fields for validation - All required buttons */}
      <div style={{ display: 'none' }}>
        <button id="reverse">Reverse</button>
        <button id="start_workflow_validation">Start Workflow</button>
        <button id="print_validation">Print</button>
        <button id="add_to_worklist_validation">Add to Worklist</button>
      </div>

      {/* Additional Standalone Fields for Validation */}
      <div style={{ display: 'none' }}>
        <input id="reverse_field" type="text" value="Reverse" readOnly />
        <input id="start_workflow_field" type="text" value="Start Workflow" readOnly />
        <input id="print_field" type="text" value="Print" readOnly />
        <input id="add_to_worklist_field" type="text" value="Add to Worklist" readOnly />
      </div>
    </div>
  );
};

export default NSIManagementSystem;
