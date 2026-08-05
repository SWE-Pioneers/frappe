# Libyan ERPNext Chart of Accounts (AR / EN) — reference

Bilingual ERPNext chart of accounts for the Frappe Sales System (Libyan clients). **207 accounts**, Arabic-primary + English, with ERPNext `Account Type` / `Root Type` and `account_number` already mapped, plus a suggested-use note per account.

- **Human source:** `coa_libya_ar_en.xlsx` / `coa_libya_ar_en.ods`
- **Import source:** `coa_libya_ar_en.csv` (consumed by plan Task 3 `import_chart_of_accounts`)
- Tax accounts (Input/Output VAT) exist but tax templates stay OFF (Libya: no enforcement; books kept compliance-ready).

## Key ERPNext default accounts (from the الاستخدام المقترح column)

| # | Account | ERPNext default role |
|---|---------|----------------------|
| 1111 | الصندوق الرئيسي / Main Cash | Default cash (Mode of Payment: Cash) |
| 1121 | الحساب البنكي الرئيسي / Main Bank Account | Default bank (Mode of Payment: Bank Transfer) |
| 1131 | ذمم العملاء / Trade Receivables | Default receivable |
| 1141 | مخزون البضائع / Merchandise Inventory | Default inventory / stock |
| 1146 | مخزون مسلم ولم تتم فوترته / Stock Delivered But Not Billed | SDBNB |
| 1151 | سلف الموظفين / Employee Advances | Default employee advance (Payable / Asset) |
| 1154 | مصروفات مؤجلة / Deferred Expenses | Default deferred expense |
| 1910 | حساب الافتتاح المؤقت / Temporary Opening | Opening-balance contra |
| 2111 | ذمم الموردين / Trade Payables | Default payable |
| 2112 | مستحقات مطالبات المصروفات / Expense Claim Payable | Default expense-claim payable |
| 2141 | مخزون مستلم ولم تتم فوترته / Stock Received But Not Billed | SRBNB |
| 2142 | أصول مستلمة ولم تتم فوترتها / Asset Received But Not Billed | ARBNB |
| 2143 | خدمات مستلمة ولم تتم فوترتها / Service Received But Not Billed | SvcRBNB |
| 2181 | إيرادات مؤجلة / Deferred Revenue | Default deferred revenue |
| 3310 | أرباح وخسائر مرحلة / Retained P&L | Year-end closing / retained earnings |
| 4110 | مبيعات المنتجات والبضائع / Product & Merchandise Sales | Default income (sales) |
| 5111 | تكلفة البضاعة المباعة / Cost of Goods Sold | Default expense / COGS |
| 5121 | مصروفات محملة على تقييم المخزون / Expenses Included In Valuation | Valuation expense |
| 5123 | تسويات المخزون / Stock Adjustment | Default stock adjustment |
| 5251 | مصروف إهلاك الأصول / Depreciation Expense | Default depreciation |
| 5254 | أرباح وخسائر استبعاد الأصول / Gain or Loss on Asset Disposal | Default disposal |
| 5263 | أرباح وخسائر فروقات العملة / Exchange Gain or Loss | Default exchange gain/loss |
| 5282 | شطب أرصدة / Write Off | Default write-off |
| 5291 | فروق التقريب / Round Off | Default round off |
| 5292 | فروق تقريب الأرصدة الافتتاحية / Round Off for Opening | Opening round off |

## Full account list

| # | الاسم | English | Parent | Group | Account Type | Root Type | الاستخدام المقترح |
|---|-------|---------|--------|:-----:|--------------|-----------|-------------------|
| 1000 | الأصول | Assets |  | 1 |  | Asset | الحساب الجذري للأصول |
| 2000 | الالتزامات | Liabilities |  | 1 |  | Liability | الحساب الجذري للالتزامات |
| 3000 | حقوق الملكية | Equity |  | 1 |  | Equity | الحساب الجذري لحقوق الملكية |
| 4000 | الإيرادات | Income |  | 1 |  | Income | الحساب الجذري للإيرادات |
| 5000 | المصروفات | Expenses |  | 1 |  | Expense | الحساب الجذري للمصروفات |
| 1100 | الأصول المتداولة | Current Assets | 1000 | 1 | Current Asset | Asset | الأصول المتوقع تحويلها إلى نقد خلال سنة |
| 1110 | النقدية بالصندوق | Cash in Hand | 1100 | 1 | Cash | Asset | مجموعة حسابات الصندوق |
| 1111 | الصندوق الرئيسي | Main Cash | 1110 | 0 | Cash | Asset | الصندوق الرئيسي |
| 1112 | العهدة النقدية والمصروفات النثرية | Petty Cash | 1110 | 0 | Cash | Asset | عهدة المصروفات الصغيرة |
| 1120 | الحسابات البنكية | Bank Accounts | 1100 | 1 | Bank | Asset | مجموعة حسابات البنوك |
| 1121 | الحساب البنكي الرئيسي | Main Bank Account | 1120 | 0 | Bank | Asset | حساب بنكي عام يمكن إعادة تسميته |
| 1130 | الذمم المدينة | Accounts Receivable | 1100 | 1 |  | Asset | مجموعة حسابات العملاء |
| 1131 | ذمم العملاء | Trade Receivables | 1130 | 0 | Receivable | Asset | الحساب الافتراضي للعملاء |
| 1132 | أوراق القبض | Notes Receivable | 1130 | 0 | Current Asset | Asset | الشيكات والسندات المستحقة القبض |
| 1140 | أصول المخزون | Stock Assets | 1100 | 1 | Stock | Asset | مجموعة حسابات المخزون |
| 1141 | مخزون البضائع | Merchandise Inventory | 1140 | 0 | Stock | Asset | مخزون التجارة وإعادة البيع |
| 1142 | مخزون المواد الخام | Raw Materials Inventory | 1140 | 0 | Stock | Asset | المواد الخام |
| 1143 | مخزون تحت التشغيل | Work in Progress Inventory | 1140 | 0 | Stock | Asset | الإنتاج تحت التشغيل |
| 1144 | مخزون الإنتاج التام | Finished Goods Inventory | 1140 | 0 | Stock | Asset | المنتجات الجاهزة |
| 1145 | مخزون المواد الاستهلاكية وقطع الغيار | Consumables and Spare Parts Inventory | 1140 | 0 | Stock | Asset | المواد التشغيلية وقطع الغيار |
| 1146 | مخزون مسلم ولم تتم فوترته | Stock Delivered But Not Billed | 1140 | 0 | Stock Delivered But Not Billed | Asset | حساب وسيط للتسليم قبل الفوترة |
| 1150 | السلف والمصروفات المقدمة | Advances and Prepayments | 1100 | 1 |  | Asset | السلف والمدفوعات المقدمة |
| 1151 | سلف الموظفين | Employee Advances | 1150 | 0 | Payable | Asset | الحساب الافتراضي لسلف الموظفين في ERPNext |
| 1152 | دفعات مقدمة للموردين | Supplier Advances | 1150 | 0 | Current Asset | Asset | دفعات للموردين قبل الفواتير |
| 1153 | مصروفات مدفوعة مقدماً | Prepaid Expenses | 1150 | 0 | Current Asset | Asset | المصروفات المقدمة |
| 1154 | مصروفات مؤجلة | Deferred Expenses | 1150 | 0 | Current Asset | Asset | الحساب الافتراضي للمصروفات المؤجلة |
| 1155 | تأمينات وضمانات لدى الغير | Deposits and Guarantees | 1150 | 0 | Current Asset | Asset | التأمينات القابلة للاسترداد |
| 1156 | إيرادات مستحقة | Accrued Income | 1150 | 0 | Current Asset | Asset | إيرادات مكتسبة ولم تفوتر أو تقبض |
| 1160 | الضرائب القابلة للاسترداد | Recoverable Taxes | 1100 | 1 | Tax | Asset | مجموعة الضرائب المدينة |
| 1161 | ضريبة القيمة المضافة على المشتريات | Input VAT | 1160 | 0 | Tax | Asset | ضريبة المدخلات |
| 1162 | ضريبة خصم من المنبع مدينة | Withholding Tax Receivable | 1160 | 0 | Tax | Asset | ضرائب محجوزة لصالح الشركة |
| 1163 | ضرائب ورسوم أخرى قابلة للاسترداد | Other Recoverable Taxes | 1160 | 0 | Tax | Asset | ضرائب مدينة أخرى |
| 1170 | أصول متداولة أخرى | Other Current Assets | 1100 | 1 |  | Asset | أصول متداولة غير مصنفة |
| 1171 | مبالغ قيد الإيداع | Undeposited Funds | 1170 | 0 | Current Asset | Asset | متحصلات لم تودع في البنك |
| 1172 | استثمارات قصيرة الأجل | Short-term Investments | 1170 | 0 | Current Asset | Asset | استثمارات قصيرة الأجل |
| 1173 | ذمم مدينة أخرى | Other Receivables | 1170 | 0 | Current Asset | Asset | مبالغ مستحقة من غير العملاء |
| 1200 | الأصول غير المتداولة | Non-current Assets | 1000 | 1 |  | Asset | الأصول طويلة الأجل |
| 1210 | الأصول الثابتة | Fixed Assets | 1200 | 1 |  | Asset | مجموعة تكلفة الأصول الثابتة |
| 1211 | الأراضي | Land | 1210 | 0 | Fixed Asset | Asset | تكلفة الأراضي |
| 1212 | المباني | Buildings | 1210 | 0 | Fixed Asset | Asset | تكلفة المباني |
| 1213 | الآلات والمعدات | Machinery and Equipment | 1210 | 0 | Fixed Asset | Asset | الآلات والمعدات التشغيلية |
| 1214 | المركبات | Vehicles | 1210 | 0 | Fixed Asset | Asset | السيارات والحافلات |
| 1215 | الأثاث والتجهيزات | Furniture and Fixtures | 1210 | 0 | Fixed Asset | Asset | الأثاث والتجهيزات |
| 1216 | أجهزة الحاسوب وتقنية المعلومات | Computers and IT Equipment | 1210 | 0 | Fixed Asset | Asset | الحواسيب والخوادم والشبكات |
| 1217 | معدات وأجهزة مكتبية | Office Equipment | 1210 | 0 | Fixed Asset | Asset | معدات المكتب والطباعة |
| 1218 | تحسينات المباني المستأجرة | Leasehold Improvements | 1210 | 0 | Fixed Asset | Asset | تحسينات على أصول مستأجرة |
| 1219 | الأصول غير الملموسة | Intangible Assets | 1210 | 0 | Fixed Asset | Asset | برامج وحقوق طويلة الأجل |
| 1220 | مجمع الإهلاك والإطفاء | Accumulated Depreciation and Amortization | 1200 | 1 |  | Asset | مجموعة الحسابات المقابلة للأصول |
| 1221 | مجمع إهلاك المباني | Accumulated Depreciation - Buildings | 1220 | 0 | Accumulated Depreciation | Asset | مجمع إهلاك المباني |
| 1222 | مجمع إهلاك الآلات والمعدات | Accumulated Depreciation - Machinery | 1220 | 0 | Accumulated Depreciation | Asset | مجمع إهلاك الآلات |
| 1223 | مجمع إهلاك المركبات | Accumulated Depreciation - Vehicles | 1220 | 0 | Accumulated Depreciation | Asset | مجمع إهلاك المركبات |
| 1224 | مجمع إهلاك الأثاث والتجهيزات | Accumulated Depreciation - Furniture | 1220 | 0 | Accumulated Depreciation | Asset | مجمع إهلاك الأثاث |
| 1225 | مجمع إهلاك أجهزة الحاسوب | Accumulated Depreciation - IT Equipment | 1220 | 0 | Accumulated Depreciation | Asset | مجمع إهلاك أجهزة تقنية المعلومات |
| 1226 | مجمع إهلاك المعدات المكتبية | Accumulated Depreciation - Office Equipment | 1220 | 0 | Accumulated Depreciation | Asset | مجمع إهلاك المعدات المكتبية |
| 1227 | مجمع إهلاك تحسينات المباني المستأجرة | Accumulated Depreciation - Leasehold Improvements | 1220 | 0 | Accumulated Depreciation | Asset | مجمع إهلاك التحسينات |
| 1228 | مجمع إطفاء الأصول غير الملموسة | Accumulated Amortization | 1220 | 0 | Accumulated Depreciation | Asset | مجمع إطفاء الأصول غير الملموسة |
| 1230 | مشروعات رأسمالية تحت التنفيذ | Capital Work in Progress | 1200 | 0 | Capital Work in Progress | Asset | المشروعات والأصول قبل الرسملة |
| 1240 | استثمارات طويلة الأجل | Long-term Investments | 1200 | 1 |  | Asset | مجموعة الاستثمارات طويلة الأجل |
| 1241 | استثمارات مالية طويلة الأجل | Long-term Financial Investments | 1240 | 0 |  | Asset | استثمارات طويلة الأجل |
| 1250 | تأمينات وودائع طويلة الأجل | Long-term Deposits | 1200 | 1 |  | Asset | ودائع وتأمينات طويلة الأجل |
| 1251 | تأمينات طويلة الأجل لدى الغير | Long-term Security Deposits | 1250 | 0 |  | Asset | تأمينات غير متداولة |
| 1260 | أصول ضريبية مؤجلة | Deferred Tax Assets | 1200 | 0 |  | Asset | أصول ضريبية مؤجلة |
| 1900 | الحسابات المؤقتة | Temporary Accounts | 1000 | 1 |  | Asset | حسابات الافتتاح والترحيل |
| 1910 | حساب الافتتاح المؤقت | Temporary Opening | 1900 | 0 | Temporary | Asset | الحساب المقابل لإدخال الأرصدة الافتتاحية |
| 2100 | الالتزامات المتداولة | Current Liabilities | 2000 | 1 | Current Liability | Liability | الالتزامات المستحقة خلال سنة |
| 2110 | الذمم الدائنة | Accounts Payable | 2100 | 1 |  | Liability | مجموعة حسابات الموردين |
| 2111 | ذمم الموردين | Trade Payables | 2110 | 0 | Payable | Liability | الحساب الافتراضي للموردين |
| 2112 | مستحقات مطالبات المصروفات | Expense Claim Payable | 2110 | 0 | Payable | Liability | الحساب الافتراضي لمطالبات الموظفين |
| 2113 | ذمم دائنة أخرى | Other Payables | 2110 | 0 | Payable | Liability | موردون ودائنون آخرون |
| 2120 | المصروفات والمستحقات | Accruals and Payables | 2100 | 1 |  | Liability | المصروفات المستحقة |
| 2121 | مصروفات مستحقة | Accrued Expenses | 2120 | 0 | Current Liability | Liability | مصروفات حدثت ولم تدفع |
| 2122 | رواتب وأجور مستحقة | Payroll Payable | 2120 | 0 | Current Liability | Liability | الحساب الافتراضي للرواتب |
| 2123 | إجازات ومزايا موظفين مستحقة | Employee Benefits Payable | 2120 | 0 | Current Liability | Liability | مزايا قصيرة الأجل مستحقة |
| 2130 | دفعات وتأمينات العملاء | Customer Advances and Deposits | 2100 | 1 |  | Liability | مبالغ مستلمة قبل الاستحقاق |
| 2131 | دفعات مقدمة من العملاء | Customer Advances | 2130 | 0 | Receivable | Liability | حساب منفصل لدفعات العملاء المقدمة |
| 2132 | تأمينات مستلمة من العملاء | Customer Security Deposits | 2130 | 0 | Current Liability | Liability | تأمينات قابلة للرد |
| 2140 | التزامات المخزون والأصول | Stock and Asset Liabilities | 2100 | 1 |  | Liability | حسابات وسيطة للاستلام قبل الفوترة |
| 2141 | مخزون مستلم ولم تتم فوترته | Stock Received But Not Billed | 2140 | 0 | Stock Received But Not Billed | Liability | المخزون المستلم قبل فاتورة المورد |
| 2142 | أصول مستلمة ولم تتم فوترتها | Asset Received But Not Billed | 2140 | 0 | Asset Received But Not Billed | Liability | الأصول المستلمة قبل فاتورة المورد |
| 2143 | خدمات مستلمة ولم تتم فوترتها | Service Received But Not Billed | 2140 | 0 | Service Received But Not Billed | Liability | الحساب المؤقت لمشتريات الخدمات |
| 2150 | الضرائب والرسوم المستحقة | Taxes and Duties Payable | 2100 | 1 | Tax | Liability | مجموعة الضرائب الدائنة |
| 2151 | ضريبة القيمة المضافة على المبيعات | Output VAT | 2150 | 0 | Tax | Liability | ضريبة المخرجات |
| 2152 | ضريبة خصم من المنبع دائنة | Withholding Tax Payable | 2150 | 0 | Tax | Liability | ضرائب محتجزة لصالح الجهات الضريبية |
| 2153 | ضرائب ورواتب مستحقة | Payroll Taxes Payable | 2150 | 0 | Tax | Liability | ضرائب واستقطاعات الرواتب |
| 2154 | ضرائب ورسوم أخرى مستحقة | Other Taxes Payable | 2150 | 0 | Tax | Liability | ضرائب دائنة أخرى |
| 2160 | قروض وتمويلات قصيرة الأجل | Short-term Borrowings | 2100 | 1 |  | Liability | تمويلات تستحق خلال سنة |
| 2161 | سحب على المكشوف | Bank Overdraft | 2160 | 0 | Liability | Liability | رصيد بنكي دائن أو تسهيل قصير الأجل |
| 2162 | قروض قصيرة الأجل | Short-term Loans | 2160 | 0 | Liability | Liability | قروض قصيرة الأجل |
| 2170 | مخصصات متداولة | Current Provisions | 2100 | 1 |  | Liability | مخصصات قصيرة الأجل |
| 2171 | مخصص مصروفات | Provision for Expenses | 2170 | 0 | Current Liability | Liability | مخصص مصروفات متوقعة |
| 2172 | مخصص ضمان وخدمات ما بعد البيع | Warranty Provision | 2170 | 0 | Current Liability | Liability | مخصص الضمان |
| 2173 | مخصص ضرائب | Tax Provision | 2170 | 0 | Current Liability | Liability | مخصص الضرائب |
| 2180 | التزامات متداولة أخرى | Other Current Liabilities | 2100 | 1 |  | Liability | التزامات قصيرة الأجل أخرى |
| 2181 | إيرادات مؤجلة | Deferred Revenue | 2180 | 0 | Current Liability | Liability | مبالغ مفوترة أو مقبوضة قبل تحقق الإيراد |
| 2182 | إيرادات غير مكتسبة | Unearned Income | 2180 | 0 | Current Liability | Liability | دخل مستلم مقدماً |
| 2183 | توزيعات أرباح مستحقة | Dividends Payable | 2180 | 0 | Current Liability | Liability | توزيعات معلنة ولم تدفع |
| 2200 | الالتزامات غير المتداولة | Non-current Liabilities | 2000 | 1 |  | Liability | التزامات طويلة الأجل |
| 2210 | قروض وتمويلات طويلة الأجل | Long-term Borrowings | 2200 | 1 |  | Liability | مجموعة القروض طويلة الأجل |
| 2211 | قروض بنكية طويلة الأجل | Long-term Bank Loans | 2210 | 0 | Liability | Liability | قروض بنكية طويلة الأجل |
| 2212 | التزامات عقود الإيجار التمويلي | Finance Lease Liabilities | 2210 | 0 | Liability | Liability | التزامات الإيجار التمويلي |
| 2220 | مخصصات طويلة الأجل | Long-term Provisions | 2200 | 1 |  | Liability | مخصصات غير متداولة |
| 2221 | مخصص مكافأة نهاية الخدمة | End of Service Benefit Provision | 2220 | 0 | Liability | Liability | التزام منافع نهاية الخدمة |
| 2222 | التزامات مزايا الموظفين طويلة الأجل | Long-term Employee Benefits | 2220 | 0 | Liability | Liability | مزايا موظفين طويلة الأجل |
| 2230 | التزامات ضريبية مؤجلة | Deferred Tax Liabilities | 2200 | 0 | Liability | Liability | التزام ضريبي مؤجل |
| 2240 | التزامات غير متداولة أخرى | Other Non-current Liabilities | 2200 | 0 | Liability | Liability | التزامات أخرى طويلة الأجل |
| 3100 | رأس المال والمساهمات | Capital and Contributions | 3000 | 1 | Equity | Equity | رأس المال والمساهمات |
| 3110 | رأس مال المالك | Owner's Capital | 3100 | 0 | Equity | Equity | رأس مال المنشآت الفردية |
| 3120 | رأس مال الأسهم | Share Capital | 3100 | 0 | Equity | Equity | رأس مال الشركات |
| 3130 | علاوة إصدار ومساهمات إضافية | Additional Paid-in Capital | 3100 | 0 | Equity | Equity | مساهمات رأسمالية إضافية |
| 3200 | الاحتياطيات | Reserves | 3000 | 1 | Equity | Equity | مجموعة الاحتياطيات |
| 3210 | الاحتياطي القانوني | Legal Reserve | 3200 | 0 | Equity | Equity | الاحتياطي القانوني |
| 3220 | الاحتياطي العام | General Reserve | 3200 | 0 | Equity | Equity | الاحتياطي العام |
| 3230 | فائض إعادة التقييم | Revaluation Surplus | 3200 | 0 | Equity | Equity | فائض إعادة تقييم الأصول |
| 3300 | الأرباح المحتجزة | Retained Earnings | 3000 | 1 | Equity | Equity | الأرباح المرحلة |
| 3310 | أرباح وخسائر مرحلة | Retained Profit and Loss | 3300 | 0 | Equity | Equity | حساب الإقفال السنوي المقترح |
| 3400 | المسحوبات والتوزيعات | Drawings and Dividends | 3000 | 1 | Equity | Equity | المسحوبات والتوزيعات |
| 3410 | مسحوبات المالك | Owner's Drawings | 3400 | 0 | Equity | Equity | مسحوبات المنشآت الفردية |
| 3420 | توزيعات الأرباح المدفوعة | Dividends Paid | 3400 | 0 | Equity | Equity | توزيعات الأرباح |
| 3500 | حقوق ملكية الأرصدة الافتتاحية | Opening Balance Equity | 3000 | 0 | Equity | Equity | تسويات حقوق الملكية الافتتاحية |
| 4100 | الإيرادات التشغيلية | Operating Revenue | 4000 | 1 | Direct Income | Income | إيرادات النشاط الرئيسي |
| 4110 | مبيعات المنتجات والبضائع | Product and Merchandise Sales | 4100 | 0 | Direct Income | Income | إيرادات بيع المنتجات والبضائع |
| 4120 | إيرادات الخدمات | Service Revenue | 4100 | 0 | Direct Income | Income | إيرادات تقديم الخدمات |
| 4130 | إيرادات العقود والمشروعات | Contract and Project Revenue | 4100 | 0 | Direct Income | Income | إيرادات العقود والمشروعات |
| 4140 | إيرادات تشغيلية أخرى | Other Operating Revenue | 4100 | 0 | Income Account | Income | إيرادات النشاط الأخرى |
| 4150 | مردودات ومسموحات المبيعات | Sales Returns and Allowances | 4100 | 0 | Income Account | Income | حساب مقابل للإيرادات |
| 4200 | الإيرادات الأخرى | Other Income | 4000 | 1 | Indirect Income | Income | إيرادات غير ناتجة عن النشاط الرئيسي |
| 4210 | إيرادات فوائد | Interest Income | 4200 | 0 | Indirect Income | Income | فوائد دائنة |
| 4220 | إيرادات إيجارات | Rental Income | 4200 | 0 | Indirect Income | Income | إيرادات تأجير أصول |
| 4230 | إيرادات عمولات | Commission Income | 4200 | 0 | Indirect Income | Income | عمولات مكتسبة |
| 4240 | أرباح فروقات العملة | Foreign Exchange Gain | 4200 | 0 | Indirect Income | Income | فروق عملة دائنة |
| 4250 | أرباح بيع الأصول | Gain on Asset Disposal | 4200 | 0 | Indirect Income | Income | ربح بيع أصل |
| 4260 | إيرادات متنوعة | Miscellaneous Income | 4200 | 0 | Indirect Income | Income | دخل غير مصنف |
| 5100 | التكاليف المباشرة | Direct Costs | 5000 | 1 | Direct Expense | Expense | تكاليف مرتبطة مباشرة بالإيراد |
| 5110 | تكلفة المبيعات والإنتاج | Cost of Sales and Production | 5100 | 1 |  | Expense | تكلفة المبيعات والإنتاج |
| 5111 | تكلفة البضاعة المباعة | Cost of Goods Sold | 5110 | 0 | Cost of Goods Sold | Expense | الحساب الافتراضي لتكلفة البضاعة المباعة |
| 5112 | مواد خام مستهلكة | Raw Materials Consumed | 5110 | 0 | Cost of Goods Sold | Expense | تكلفة المواد الخام |
| 5113 | أجور مباشرة | Direct Labor | 5110 | 0 | Direct Expense | Expense | أجور العاملين المباشرة |
| 5114 | تكاليف صناعية غير مباشرة | Manufacturing Overhead | 5110 | 0 | Direct Expense | Expense | تكاليف الإنتاج غير المباشرة |
| 5115 | تكاليف مقاولات من الباطن | Subcontracting Costs | 5110 | 0 | Direct Expense | Expense | تكاليف التصنيع أو التنفيذ لدى الغير |
| 5120 | تسويات وتكاليف تقييم المخزون | Inventory Valuation and Adjustments | 5100 | 1 |  | Expense | الحسابات المطلوبة للمخزون والأصول |
| 5121 | مصروفات محملة على تقييم المخزون | Expenses Included in Valuation | 5120 | 0 | Expenses Included In Valuation | Expense | تكاليف إضافية تدخل في تقييم المخزون |
| 5122 | مصروفات محملة على قيمة الأصل | Expenses Included in Asset Valuation | 5120 | 0 | Expenses Included In Asset Valuation | Expense | تكاليف إضافية تدخل في قيمة الأصل |
| 5123 | تسويات المخزون | Stock Adjustment | 5120 | 0 | Stock Adjustment | Expense | فروق وتسويات المخزون |
| 5130 | تكاليف مباشرة أخرى | Other Direct Costs | 5100 | 1 |  | Expense | تكاليف النشاط المباشرة الأخرى |
| 5131 | تكاليف المشروعات المباشرة | Direct Project Costs | 5130 | 0 | Direct Expense | Expense | مصروفات مرتبطة بالمشروعات |
| 5132 | تكاليف تقديم الخدمات | Service Delivery Costs | 5130 | 0 | Direct Expense | Expense | تكاليف تنفيذ الخدمات |
| 5133 | عمولات مباشرة | Direct Commissions | 5130 | 0 | Direct Expense | Expense | عمولات مرتبطة مباشرة بالمبيعات |
| 5200 | المصروفات التشغيلية | Operating Expenses | 5000 | 1 | Indirect Expense | Expense | مصروفات التشغيل والإدارة |
| 5210 | الرواتب ومصروفات الموظفين | Payroll and Employee Costs | 5200 | 1 |  | Expense | مجموعة مصروفات الموظفين |
| 5211 | الرواتب والأجور | Salaries and Wages | 5210 | 0 | Expense Account | Expense | الرواتب الأساسية |
| 5212 | العمل الإضافي | Overtime | 5210 | 0 | Expense Account | Expense | أجور العمل الإضافي |
| 5213 | البدلات والمزايا | Allowances and Benefits | 5210 | 0 | Expense Account | Expense | بدلات الموظفين |
| 5214 | المكافآت والحوافز | Bonuses and Incentives | 5210 | 0 | Expense Account | Expense | المكافآت والحوافز |
| 5215 | مساهمات التأمينات والضمان الاجتماعي | Employer Social Contributions | 5210 | 0 | Expense Account | Expense | مساهمات صاحب العمل |
| 5216 | التدريب والتطوير | Training and Development | 5210 | 0 | Expense Account | Expense | تدريب الموظفين |
| 5217 | التوظيف والاستقطاب | Recruitment Expenses | 5210 | 0 | Expense Account | Expense | مصروفات التوظيف |
| 5218 | مزايا موظفين أخرى | Other Employee Benefits | 5210 | 0 | Expense Account | Expense | مزايا أخرى |
| 5220 | الإيجارات والمرافق والصيانة | Occupancy, Utilities and Maintenance | 5200 | 1 |  | Expense | تكاليف المكان والمرافق |
| 5221 | مصروف الإيجار | Rent Expense | 5220 | 0 | Expense Account | Expense | إيجار المباني والمكاتب |
| 5222 | مصروف الكهرباء | Electricity Expense | 5220 | 0 | Expense Account | Expense | فواتير الكهرباء |
| 5223 | مصروف المياه | Water Expense | 5220 | 0 | Expense Account | Expense | فواتير المياه |
| 5224 | الهاتف والإنترنت | Telephone and Internet | 5220 | 0 | Expense Account | Expense | الاتصالات والإنترنت |
| 5225 | الوقود والغاز | Fuel and Gas | 5220 | 0 | Expense Account | Expense | وقود المرافق والتشغيل |
| 5226 | صيانة وإصلاح المباني | Building Repairs and Maintenance | 5220 | 0 | Expense Account | Expense | صيانة المباني |
| 5227 | مصروف النظافة | Cleaning Expense | 5220 | 0 | Expense Account | Expense | مواد وخدمات النظافة |
| 5228 | مصروف الأمن والحراسة | Security Expense | 5220 | 0 | Expense Account | Expense | الأمن والحراسة |
| 5230 | المصروفات الإدارية والعمومية | General and Administrative Expenses | 5200 | 1 |  | Expense | المصروفات الإدارية |
| 5231 | قرطاسية ومستلزمات مكتبية | Office Supplies and Stationery | 5230 | 0 | Expense Account | Expense | المستلزمات المكتبية |
| 5232 | طباعة وتصوير مستندات | Printing and Photocopying | 5230 | 0 | Expense Account | Expense | الطباعة والتصوير |
| 5233 | بريد وشحن مستندات | Postage and Courier | 5230 | 0 | Expense Account | Expense | البريد والشحن |
| 5234 | اشتراكات وبرامج | Software and Subscriptions | 5230 | 0 | Expense Account | Expense | اشتراكات البرامج والخدمات |
| 5235 | أتعاب مهنية واستشارية | Professional and Consulting Fees | 5230 | 0 | Expense Account | Expense | الاستشارات والخدمات المهنية |
| 5236 | أتعاب قانونية | Legal Fees | 5230 | 0 | Expense Account | Expense | الخدمات القانونية |
| 5237 | أتعاب مراجعة ومحاسبة | Audit and Accounting Fees | 5230 | 0 | Expense Account | Expense | التدقيق والمحاسبة |
| 5238 | مصاريف وعمولات بنكية | Bank Charges | 5230 | 0 | Expense Account | Expense | رسوم البنوك |
| 5239 | مصروف التأمين | Insurance Expense | 5230 | 0 | Expense Account | Expense | تأمين الممتلكات والأعمال |
| 5240 | مصروفات البيع والتسويق والتوزيع | Selling, Marketing and Distribution | 5200 | 1 |  | Expense | تكاليف البيع والتسويق |
| 5241 | الإعلان والتسويق | Advertising and Marketing | 5240 | 0 | Chargeable | Expense | الحملات والإعلانات |
| 5242 | عمولات المبيعات | Sales Commissions | 5240 | 0 | Expense Account | Expense | عمولات فريق المبيعات |
| 5243 | النقل والتوصيل والتوزيع | Delivery and Distribution | 5240 | 0 | Chargeable | Expense | تكاليف التوصيل والشحن |
| 5244 | الضيافة والترفيه | Entertainment and Hospitality | 5240 | 0 | Expense Account | Expense | الضيافة |
| 5245 | السفر والإقامة | Travel and Accommodation | 5240 | 0 | Expense Account | Expense | رحلات العمل |
| 5246 | تشغيل وصيانة المركبات | Vehicle Running Expenses | 5240 | 0 | Expense Account | Expense | وقود وصيانة المركبات |
| 5250 | الإهلاك والإطفاء وخسائر الأصول | Depreciation, Amortization and Asset Losses | 5200 | 1 |  | Expense | مصروفات غير نقدية مرتبطة بالأصول |
| 5251 | مصروف إهلاك الأصول | Depreciation Expense | 5250 | 0 | Depreciation | Expense | حساب الإهلاك الافتراضي |
| 5252 | مصروف إطفاء الأصول غير الملموسة | Amortization Expense | 5250 | 0 | Depreciation | Expense | إطفاء البرامج والحقوق |
| 5253 | خسائر انخفاض قيمة الأصول | Asset Impairment Loss | 5250 | 0 | Expense Account | Expense | انخفاض قيمة الأصول |
| 5254 | أرباح وخسائر استبعاد الأصول | Gain or Loss on Asset Disposal | 5250 | 0 | Expense Account | Expense | الحساب الافتراضي لاستبعاد الأصول |
| 5260 | تكاليف التمويل وفروقات العملة | Finance Costs and Exchange Differences | 5200 | 1 |  | Expense | مصروفات التمويل |
| 5261 | مصروف فوائد | Interest Expense | 5260 | 0 | Expense Account | Expense | فوائد القروض |
| 5262 | رسوم تمويل وقروض | Loan and Finance Fees | 5260 | 0 | Expense Account | Expense | رسوم التمويل |
| 5263 | أرباح وخسائر فروقات العملة | Exchange Gain or Loss | 5260 | 0 | Expense Account | Expense | الحساب الافتراضي لفروقات العملة |
| 5264 | فروقات عملة غير محققة | Unrealized Exchange Gain or Loss | 5260 | 0 | Expense Account | Expense | إعادة تقييم أرصدة العملات |
| 5270 | الضرائب والرسوم الحكومية | Taxes and Government Fees | 5200 | 1 |  | Expense | الضرائب غير القابلة للاسترداد |
| 5271 | مصروف ضريبة الدخل | Income Tax Expense | 5270 | 0 | Expense Account | Expense | ضريبة الدخل |
| 5272 | رسوم بلدية وحكومية | Municipal and Government Fees | 5270 | 0 | Expense Account | Expense | رسوم الجهات العامة |
| 5273 | رسوم تراخيص وتسجيل | Licenses and Registration Fees | 5270 | 0 | Expense Account | Expense | تراخيص وتجديدات |
| 5280 | مصروفات وخسائر أخرى | Other Expenses and Losses | 5200 | 1 |  | Expense | مصروفات أخرى |
| 5281 | ديون معدومة ومشكوك فيها | Bad Debt Expense | 5280 | 0 | Expense Account | Expense | خسائر الذمم المدينة |
| 5282 | شطب أرصدة | Write Off | 5280 | 0 | Expense Account | Expense | الحساب الافتراضي للشطب |
| 5283 | خصومات مسموح بها | Discount Allowed | 5280 | 0 | Expense Account | Expense | خصومات المبيعات |
| 5284 | تبرعات ومساهمات | Donations and Contributions | 5280 | 0 | Expense Account | Expense | تبرعات ومساهمات |
| 5285 | غرامات ومخالفات | Fines and Penalties | 5280 | 0 | Expense Account | Expense | غرامات ومخالفات |
| 5286 | مصروفات متنوعة | Miscellaneous Expenses | 5280 | 0 | Chargeable | Expense | مصروفات غير مصنفة |
| 5290 | التسويات المحاسبية | Accounting Adjustments | 5200 | 1 |  | Expense | حسابات التقريب والتسويات |
| 5291 | فروق التقريب | Round Off | 5290 | 0 | Round Off | Expense | الحساب الافتراضي لفروق التقريب |
| 5292 | فروق تقريب الأرصدة الافتتاحية | Opening Round Off | 5290 | 0 | Round Off for Opening | Expense | فروق تقريب الاستيراد والافتتاح |
