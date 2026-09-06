# POS UI audit

Audited the Classic and Modern POS layouts and all 12 dialogs against personal `develop` at `46c71c82`.
The changes use Frappe UI controls, lists, dialog behavior, typography, and color tokens.
Configured POS button colors remain available.

| Surface | Findings and changes |
| --- | --- |
| Modern POS | Widened the cart. The catalog uses one list when two lists would clip values. Added cart guidance. |
| Classic POS | Aligned cart controls and expanded fields. Kept checkout actions reachable in small windows. |
| Both layouts | Display totals as text with a prominent grand total. Keep Pay separate from secondary actions. Preserve the view toggle across layouts. |
| Cart rows | Use Frappe UI list cells with consistent height. Align numeric values and action columns. Remove empty grid cells. |
| Item grid | Limit image placeholders to two initials. Use the currency formatter. Let cards fit narrow containers. |
| Open shift | Keep the existing fixed footer behavior. Add a shared header and a wider two-column form. |
| Close shift | Keep actions visible while tables scroll. Use a neutral Cancel button and a clear Close Shift action. |
| Payment and refund | Use the shared dialog layout. Put payment fields first in small windows. Use refund-specific action labels. Match button text and height to the form inputs. |
| Keypad | Keep actions visible. Reduce key height in short windows. Disable text entry while saving. |
| Coupon code | Remove excessive spacing and the fixed-width input. Align the action buttons. |
| Price list | Remove the large empty gap. Add a field label. Hide Remove when no price list is selected. |
| Loyalty points | Remove the fixed height. Give the available points and program separate labels. |
| Item enquiry | Align fields and reduce padding. Keep Submit and Cancel visible while the form scrolls. |
| Batch selection | Show the item name. Put Cancel before Select. |
| Saved invoices | Clarify the title. Label the search field. Allow horizontal table scrolling in small windows. |
| Return invoices | Give the dialog a distinct title. Keep selection, paging, and actions visible. |
| Leave-sale confirmation | Explain the result of each action. Use separate Cancel, Discard and Continue, and Save and Continue actions. |

The browser checks cover 1440 × 900, 1024 × 640, and 390 × 560 dialog windows.
Additional checks cover cart values, expanded fields, keyboard validation, invoice selection, payment fields, and dark refund styling.
POS actions use Frappe UI's medium buttons (32px height and 14px text).
The fixture uses real Vue components, schemas, and models with in-memory data.
It rejects database writes.

The initial visual pass used the local Books test site.
The final visual pass used the isolated fixture after the local site stopped responding.
The browser fixture does not verify transaction posting.
Separate backend integration tests cover automatic POS shipments from the configured POS inventory, profile inventory, cancellation, and insufficient stock rejection.
Automatic POS shipments now use the same inventory location as the POS catalog instead of the general shipment default.
Stock errors include the location that was checked.
