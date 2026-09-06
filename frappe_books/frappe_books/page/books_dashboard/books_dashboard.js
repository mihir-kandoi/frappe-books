frappe.pages["books-dashboard"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Books Dashboard"),
		single_column: true,
	});
	page.set_primary_action(__("New Sales Invoice"), () => frappe.new_doc("Books Sales Invoice"),
		"add");
	page.add_inner_button(__("Point of Sale"), () => frappe.set_route("books-pos"));
	page.add_inner_button(__("Refresh"), () => load_dashboard(wrapper));
	$(wrapper).find(".layout-main-section").html('<div class="books-dashboard-root"></div>');
	load_dashboard(wrapper);
};

frappe.pages["books-dashboard"].on_page_show = function (wrapper) {
	if ($(wrapper).find(".books-dashboard-root").is(":empty")) load_dashboard(wrapper);
};

async function load_dashboard(wrapper) {
	const root = $(wrapper).find(".books-dashboard-root");
	root.html(`<div class="books-loading">${__("Loading your books…")}</div>`);
	try {
		const { message: data } = await frappe.call("frappe_books.dashboard.get_dashboard_data");
		render_dashboard(root, data);
	} catch (error) {
		root.html(`<div class="books-empty">${__("Could not load the dashboard.")}</div>`);
		throw error;
	}
}

function render_dashboard(root, data) {
	const cards = [
		[__("Sales"), data.summary.sales, "sales", "Books Sales Invoice"],
		[__("Purchases"), data.summary.purchases, "purchases", "Books Purchase Invoice"],
		[__("Receivable"), data.summary.receivable, "receivable", "Books Sales Invoice"],
		[__("Payable"), data.summary.payable, "payable", "Books Purchase Invoice"],
		[__("Net Profit"), data.summary.profit, "profit", "Books Profit and Loss"],
	];
	root.html(`
		<section class="books-dashboard-hero">
			<div><p>${__("Company overview")}</p><h2>${escape_html(data.company)}</h2></div>
			<div class="books-period">${frappe.datetime.str_to_user(data.period.from_date)} — ${frappe.datetime.str_to_user(data.period.to_date)}</div>
		</section>
		<section class="books-kpis">${cards
			.map(
				([label, value, tone, target]) => `<button class="books-kpi ${tone}" data-target="${target}">
					<span>${label}</span><strong>${money(value)}</strong>
				</button>`
			)
			.join("")}</section>
		<section class="books-dashboard-grid">
			<article class="books-panel books-trend-panel"><div class="books-panel-title"><div><p>${__("Six month trend")}</p><h3>${__("Sales and purchases")}</h3></div></div><div class="books-trend"></div></article>
			${unpaid_panel(__("Unpaid sales invoices"), data.unpaid_sales, "Books Sales Invoice")}
			${unpaid_panel(__("Unpaid purchase invoices"), data.unpaid_purchases, "Books Purchase Invoice")}
		</section>`);

	root.find(".books-kpi").on("click", function () {
		const target = $(this).data("target");
		if (target === "Books Profit and Loss") frappe.set_route("query-report", target);
		else frappe.set_route("List", target);
	});
	root.find("[data-document]").on("click", function () {
		frappe.set_route("Form", $(this).data("doctype"), $(this).data("document"));
	});

	const chartTarget = root.find(".books-trend").get(0);
	if (data.trend.length && frappe.Chart) {
		new frappe.Chart(chartTarget, {
			type: "bar",
			height: 250,
			colors: ["#0f766e", "#d97706"],
			data: {
				labels: data.trend.map((row) => row.label),
				datasets: [
					{ name: __("Sales"), values: data.trend.map((row) => row.sales) },
					{ name: __("Purchases"), values: data.trend.map((row) => row.purchases) },
				],
			},
			axisOptions: { xIsSeries: true },
			barOptions: { spaceRatio: 0.35 },
		});
	}
}

function unpaid_panel(title, rows, doctype) {
	const content = rows.length
		? rows
				.map(
					(row) => `<button class="books-unpaid-row" data-doctype="${doctype}" data-document="${escape_html(row.name)}">
						<span><strong>${escape_html(row.party)}</strong><small>${escape_html(row.name)} · ${frappe.datetime.str_to_user(row.date)}</small></span>
						<b>${money(row.outstanding_amount)}</b>
					</button>`
				)
				.join("")
		: `<div class="books-empty">${__("Nothing outstanding")}</div>`;
	return `<article class="books-panel"><div class="books-panel-title"><h3>${title}</h3></div><div>${content}</div></article>`;
}

function money(value) {
	return frappe.format(value || 0, { fieldtype: "Currency" });
}

function escape_html(value) {
	return frappe.utils.escape_html(String(value || ""));
}
