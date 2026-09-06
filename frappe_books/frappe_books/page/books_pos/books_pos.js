frappe.pages["books-pos"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Point of Sale"),
		single_column: true,
	});
	page.add_inner_button(__("Open Shift"), () => frappe.new_doc("Books Pos Opening Shift"));
	page.add_inner_button(__("Close Shift"), () => frappe.new_doc("Books Pos Closing Shift"));
	page.add_inner_button(__("POS Settings"), () => frappe.set_route("Form", "Books Pos Settings"));
	$(wrapper).find(".layout-main-section").html('<div class="books-pos-root"></div>');
	wrapper.books_pos = new BooksPOS($(wrapper).find(".books-pos-root"));
};

frappe.pages["books-pos"].on_page_show = function (wrapper) {
	wrapper.books_pos?.load();
};

class BooksPOS {
	constructor(root) {
		this.root = root;
		this.cart = [];
		this.context = null;
		this.search = "";
	}

	async load(search = "") {
		this.search = search;
		if (!this.context) this.root.html(`<div class="books-pos-loading">${__("Loading the counter…")}</div>`);
		const { message } = await frappe.call({
			method: "frappe_books.commerce.pos_api.get_pos_context",
			args: { search, limit: 100 },
		});
		this.context = message;
		this.render();
	}

	render() {
		const context = this.context;
		this.root.html(`
			<div class="books-pos-status ${context.is_shift_open ? "open" : "closed"}">
				<span><i></i>${context.is_shift_open ? __("Shift open") : __("Shift closed")}</span>
				<b>${__("Inventory")}: ${this.escape(context.location)}</b>
			</div>
			<div class="books-pos-layout">
				<section class="books-catalog">
					<div class="books-pos-search"><span>${frappe.utils.icon("search", "sm")}</span><input type="search" placeholder="${__("Search name, code, or scan barcode")}" value="${this.escape(this.search)}"></div>
					<div class="books-products">${this.product_cards()}</div>
				</section>
				<aside class="books-cart">
					<div class="books-cart-head"><div><small>${__("Current sale")}</small><h3>${__("Cart")}</h3></div><button class="btn btn-xs btn-default books-clear">${__("Clear")}</button></div>
					<div class="books-cart-items"></div>
					<div class="books-checkout-fields">
						<label>${__("Customer")}<select class="form-control books-customer">${this.customer_options()}</select></label>
						<label>${__("Payment method")}<select class="form-control books-payment-method">${this.payment_options()}</select></label>
						<label>${__("Coupon codes")}<input class="form-control books-coupons" placeholder="${__("Comma separated")}"></label>
						<label>${__("Redeem loyalty points")}<input type="number" min="0" step="1" class="form-control books-loyalty" value="0"></label>
					</div>
					<div class="books-cart-total"><span>${__("Estimated total")}</span><strong></strong></div>
					<button class="btn btn-primary books-checkout">${__("Pay and submit")}</button>
					<div class="books-pos-result"></div>
				</aside>
			</div>`);
		this.bind();
		this.render_cart();
		if (!context.configured || !context.is_shift_open) this.render_blocker();
	}

	product_cards() {
		if (!this.context.items.length) return `<div class="books-pos-empty">${__("No items found")}</div>`;
		return this.context.items
			.map((item, index) => {
				const availability = item.track_item
					? `<small class="${item.available_quantity <= 0 ? "out" : ""}">${item.available_quantity} ${this.escape(item.unit)} ${__("available")}</small>`
					: `<small>${__("Service / untracked")}</small>`;
				return `<button class="books-product" data-index="${index}">
					<div class="books-product-image">${item.image ? `<img src="${this.escape(item.image)}">` : frappe.utils.icon("package", "lg")}</div>
					<div class="books-product-copy"><strong>${this.escape(item.name)}</strong><span>${this.escape(item.item_code || "")}</span>${availability}</div>
					<b>${this.money(item.rate)}</b>
				</button>`;
			})
			.join("");
	}

	bind() {
		const debounced = frappe.utils.debounce((value) => this.load(value), 300);
		this.root.find(".books-pos-search input").on("input", (event) => debounced(event.target.value));
		this.root.find(".books-product").on("click", (event) => {
			const item = this.context.items[Number($(event.currentTarget).data("index"))];
			this.add_item(item);
		});
		this.root.find(".books-clear").on("click", () => {
			this.cart = [];
			this.render_cart();
		});
		this.root.find(".books-checkout").on("click", () => this.checkout());
	}

	async add_item(item) {
		if (item.track_item && item.available_quantity <= 0) {
			frappe.show_alert({ message: __("This item is out of stock."), indicator: "orange" });
			return;
		}
		let inventory = {};
		if (item.has_batch || item.has_serial_number) {
			inventory = await new Promise((resolve) => {
				frappe.prompt(
					[
						{ fieldname: "batch", label: __("Batch"), fieldtype: "Link", options: "Books Batch", reqd: item.has_batch },
						{ fieldname: "serial_number", label: __("Serial Numbers"), fieldtype: "Small Text", reqd: item.has_serial_number, description: __("One serial number per line") },
					],
					(values) => resolve(values),
					__("Inventory details"),
					__("Add")
				);
			});
		}
		const key = `${item.name}|${inventory.batch || ""}|${inventory.serial_number || ""}`;
		const existing = this.cart.find((row) => row.key === key);
		if (existing) existing.quantity += 1;
		else this.cart.push({ key, item: item.name, quantity: 1, rate: item.rate || 0, ...inventory });
		this.render_cart();
	}

	render_cart() {
		const area = this.root.find(".books-cart-items");
		if (!this.cart.length) {
			area.html(`<div class="books-cart-empty">${frappe.utils.icon("shopping-cart", "lg")}<p>${__("Add an item to start a sale")}</p></div>`);
		} else {
			area.html(
				this.cart
					.map(
						(row, index) => `<div class="books-cart-row" data-index="${index}">
							<div><strong>${this.escape(row.item)}</strong>${row.batch ? `<small>${__("Batch")}: ${this.escape(row.batch)}</small>` : ""}</div>
							<input class="form-control books-qty" type="number" min="1" step="1" value="${row.quantity}">
							<input class="form-control books-rate" type="number" min="0" step="0.01" value="${row.rate}" ${this.context.can_change_rate ? "" : "disabled"}>
							<b>${this.money(row.quantity * row.rate)}</b><button class="books-remove" title="${__("Remove")}">×</button>
						</div>`
					)
					.join("")
			);
			area.find(".books-qty").on("change", (event) => this.update_row(event, "quantity"));
			area.find(".books-rate").on("change", (event) => this.update_row(event, "rate"));
			area.find(".books-remove").on("click", (event) => {
				this.cart.splice(Number($(event.currentTarget).closest(".books-cart-row").data("index")), 1);
				this.render_cart();
			});
		}
		this.root.find(".books-cart-total strong").html(this.money(this.estimated_total()));
		this.root.find(".books-checkout").prop("disabled", !this.cart.length || !this.context.is_shift_open);
	}

	update_row(event, fieldname) {
		const row = this.cart[Number($(event.currentTarget).closest(".books-cart-row").data("index"))];
		row[fieldname] = Math.max(fieldname === "quantity" ? 1 : 0, Number(event.target.value || 0));
		this.render_cart();
	}

	async checkout() {
		const customer = this.root.find(".books-customer").val();
		const paymentMethod = this.root.find(".books-payment-method").val();
		if (!customer || !paymentMethod) {
			frappe.msgprint(__("Select a customer and payment method."));
			return;
		}
		const couponCodes = this.root
			.find(".books-coupons")
			.val()
			.split(",")
			.map((value) => value.trim())
			.filter(Boolean);
		const { message } = await frappe.call({
			method: "frappe_books.commerce.pos_api.checkout",
			type: "POST",
			args: {
				cart: this.cart.map(({ item, quantity, rate, batch, serial_number }) => ({ item, quantity, rate, batch, serial_number })),
				customer,
				payments: [{ payment_method: paymentMethod }],
				coupon_codes: couponCodes,
				redeem_loyalty_points: Number(this.root.find(".books-loyalty").val() || 0),
			},
			freeze: true,
			freeze_message: __("Submitting sale…"),
		});
		this.cart = [];
		this.render_cart();
		this.root.find(".books-pos-result").html(`<div><strong>${__("Sale complete")}</strong><span>${this.escape(message.invoice)} · ${this.money(message.grand_total)}</span><button class="btn btn-xs btn-default">${__("Open invoice")}</button></div>`);
		this.root.find(".books-pos-result button").on("click", () => frappe.set_route("Form", "Books Sales Invoice", message.invoice));
		frappe.show_alert({ message: __("POS invoice submitted"), indicator: "green" });
		await this.load(this.search);
	}

	render_blocker() {
		const message = !this.context.configured
			? __("Finish POS Settings before using the counter.")
			: __("Open a shift before accepting sales.");
		this.root.find(".books-products").prepend(`<div class="books-pos-blocker"><strong>${message}</strong><button class="btn btn-sm btn-default">${!this.context.configured ? __("Open settings") : __("Open shift")}</button></div>`);
		this.root.find(".books-pos-blocker button").on("click", () => {
			if (!this.context.configured) frappe.set_route("Form", "Books Pos Settings");
			else frappe.new_doc("Books Pos Opening Shift");
		});
	}

	customer_options() {
		return `<option value="">${__("Select customer")}</option>${this.context.customers
			.map((row) => `<option value="${this.escape(row.name)}" ${row.name === this.context.default_customer ? "selected" : ""}>${this.escape(row.name)}</option>`)
			.join("")}`;
	}

	payment_options() {
		return `<option value="">${__("Select method")}</option>${this.context.payment_methods
			.map((row) => `<option value="${this.escape(row.name)}">${this.escape(row.name)}</option>`)
			.join("")}`;
	}

	estimated_total() {
		return this.cart.reduce((total, row) => total + row.quantity * row.rate, 0);
	}

	money(value) {
		return frappe.format(value || 0, { fieldtype: "Currency" });
	}

	escape(value) {
		return frappe.utils.escape_html(String(value || ""));
	}
}
