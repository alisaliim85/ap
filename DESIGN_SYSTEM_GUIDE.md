## YOUR DESIGN SYSTEM PROMPT
**Role:** Senior Frontend Developer (Django & HTMX Specialist).
**Project:** SaaS Insurance Brokerage Platform (B2B2C).
**Language/Direction:** Arabic (RTL).
**Tech Stack:** Django Templates, HTMX, Tailwind CSS (v3.4+), Alpine.js.

### 1. Design Foundations
* **Visual Style:** "Corporate & Professional" (Dense, structured, high trust).
* **Color Palette:** * Primary (Brand): Teal/Emerald (`colors.teal.600` for actions, `teal.50` for backgrounds).
    * Secondary: Slate/Gray (`slate.600` for text, `slate.200` for borders).
    * Status: Active (Green), Expired (Red), Pending (Orange/Amber).
* **Typography:** * Font Family: 'Almarai', sans-serif (Google Fonts).
    * Scaling: Base text 14px (dense data), Headings 18px-24px.
* **Shapes:** Border Radius `rounded-md` (4px-6px) for a subtle, professional look.
* **Iconography:** Duotone Style (use Phosphor Icons `ph-duotone` or similar).

### 2. Component Specifications
* **Layout:**
    * Full-width fluid container.
    * Sidebar Navigation: Vertical, Collapsible, Right-aligned (RTL).
* **Data Tables (CRITICAL):**
    * **Desktop:** Modern List Style. Horizontal dividers only (`border-b`). No vertical borders.
    * **Mobile:** Stacked Cards Pattern. Hide `<table>` rows, show grid of `div.card` for each record.
    * **Actions:** Inline icons (Edit/Delete) visible on hover or persistent in last column.
* **Forms:**
    * Style: Outlined Inputs (White bg, Slate-300 border, Teal-500 focus ring).
    * Structure: Long Scroll with Sticky Anchor Links sidebar.
    * Upload: Large Drag & Drop Zone (Dashed border, illustrating upload).
* **Feedback & Overlays:**
    * **Details/Edit:** Use **Side Drawers (Slide-overs)** coming from the LEFT (in RTL layout). Triggered via HTMX.
    * **Toasts:** Top-Center position.
* **Dashboard Widgets:** Flat cards with `border` (no shadow). Charts use distinct functional colors.

### 3. Interaction & HTMX Rules
* **Micro-interactions:** Smooth transitions (300ms ease-in-out).
* **Loading:**
    * Global: Top Progress Bar (NProgress style).
    * Local: Spinner inside buttons (`hx-indicator`).
* **Empty States:** Illustrative icon + Primary Action Button (e.g., "Create First Policy").



#####  1. حزمة المصمم (UI Designer Specs)  #####

العنصر,المواصفات والقرار
الخط (Typography),Almarai (Google Font).• العناوين: Bold (700/800).• النصوص: Regular (400).• الأرقام: يجب أن تكون واضحة جداً داخل الجداول.
الألوان (Palette),"Primary: Teal (#0d9488).Surface: White (#ffffff) & Slate-50 (#f8fafc).Text: Slate-800 (العناوين)، Slate-600 (النصوص).Status: Green (Active), Red (Expired), Orange (Pending)."
الحواف (Radius),Rounded-MD (6px): للأزرار، البطاقات، وحقول الإدخال.Rounded-LG (8px): للنوافذ المنبثقة (Drawers/Modals).
الأيقونات (Icons),Phosphor Icons (Duotone):لون التعبئة: Primary-100.لون الحدود: Primary-700.
الظلال (Elevation),Flat & Bordered:معظم العناصر (Cards/Tables) تعتمد على حدود border-slate-200 بدلاً من الظلال.Shadow-LG: فقط للنوافذ المنبثقة والقوائم المنسدلة.

#### design system ####

<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>نظام تصميم الوسيط - المرجع الشامل</title>
    
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Almarai:wght@300;400;700;800&display=swap" rel="stylesheet">
    
    <script src="https://unpkg.com/@phosphor-icons/web"></script>

    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {
            theme: {
                extend: {
                    fontFamily: { sans: ['Almarai', 'sans-serif'] },
                    colors: {
                        brand: {
                            50: '#f0fdfa', 100: '#ccfbf1', 200: '#99f6e4',
                            500: '#14b8a6', 600: '#0d9488', 700: '#0f766e', 900: '#134e4a',
                        }
                    }
                }
            }
        }
    </script>
    <script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js"></script>
    
    <style>
        /* تحسينات إضافية */
        body { background-color: #f8fafc; }
        .section-title { @apply text-xs font-bold text-slate-400 uppercase tracking-wider mb-4 border-b border-slate-200 pb-2; }
        [x-cloak] { display: none !important; }
    </style>
</head>
<body class="p-8 text-slate-800">

    <div class="max-w-6xl mx-auto space-y-12">
        
        <div class="text-center mb-12">
            <h1 class="text-4xl font-extrabold text-brand-900 mb-2">نظام تصميم "الوسيط"</h1>
            <p class="text-slate-500">الإصدار 1.0 • مخصص لمنصات التأمين SaaS</p>
        </div>

        <section>
            <h3 class="text-xs font-bold text-slate-400 uppercase mb-4 border-b pb-2">1. الألوان والطباعة (Foundations)</h3>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-8">
                <div class="space-y-2">
                    <h4 class="font-bold mb-2">لوحة الألوان (Brand Palette)</h4>
                    <div class="flex gap-2">
                        <div class="h-16 w-16 bg-brand-50 rounded shadow-sm text-xs flex items-end p-1">50</div>
                        <div class="h-16 w-16 bg-brand-100 rounded shadow-sm text-xs flex items-end p-1">100</div>
                        <div class="h-16 w-16 bg-brand-500 rounded shadow-sm text-xs flex items-end p-1 text-white">500</div>
                        <div class="h-16 w-16 bg-brand-600 rounded shadow-sm text-xs flex items-end p-1 text-white ring-2 ring-offset-2 ring-brand-600">600 (Main)</div>
                        <div class="h-16 w-16 bg-brand-900 rounded shadow-sm text-xs flex items-end p-1 text-white">900</div>
                    </div>
                </div>
                <div class="space-y-2">
                    <h4 class="font-bold mb-2">الخطوط (Almarai)</h4>
                    <h1 class="text-3xl font-extrabold">عنوان رئيسي H1</h1>
                    <h2 class="text-xl font-bold">عنوان فرعي H2</h2>
                    <p class="text-base text-slate-600">نص الفقرة الأساسي. يستخدم للقراءة الطويلة وشرح المنافع الطبية.</p>
                    <p class="text-sm text-slate-500">نص ثانوي (Caption) يستخدم للملاحظات وتواريخ الجداول.</p>
                </div>
            </div>
        </section>

        <section>
            <h3 class="text-xs font-bold text-slate-400 uppercase mb-4 border-b pb-2">2. المكونات التفاعلية (Interactive)</h3>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-8 bg-white p-6 rounded-lg border border-slate-200">
                
                <div class="space-y-4">
                    <h4 class="font-bold">الأزرار (Buttons)</h4>
                    <div class="flex flex-wrap gap-3">
                        <button class="px-4 py-2 bg-brand-600 text-white rounded-md hover:bg-brand-700 font-medium shadow-sm flex items-center gap-2">
                            <i class="ph-bold ph-check"></i> حفظ التغييرات
                        </button>
                        <button class="px-4 py-2 bg-white border border-slate-300 text-slate-700 rounded-md hover:bg-slate-50 font-medium flex items-center gap-2">
                            <i class="ph-duotone ph-x"></i> إلغاء
                        </button>
                        <button class="px-4 py-2 bg-red-50 text-red-600 rounded-md hover:bg-red-100 font-medium flex items-center gap-2">
                            <i class="ph-duotone ph-trash"></i> حذف
                        </button>
                    </div>
                </div>

                <div class="space-y-4">
                    <h4 class="font-bold">حقول الإدخال (Outlined Inputs)</h4>
                    <div>
                        <label class="block text-sm font-medium text-slate-700 mb-1">اسم الموظف</label>
                        <div class="relative">
                            <i class="ph-duotone ph-user absolute top-2.5 right-3 text-slate-400"></i>
                            <input type="text" placeholder="الاسم ثلاثي" class="w-full pl-4 pr-10 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-brand-500 focus:border-brand-500 transition">
                        </div>
                    </div>
                    <div class="flex gap-4">
                        <div class="w-1/2">
                            <label class="block text-sm font-medium text-slate-700 mb-1">الفئة</label>
                            <select class="w-full px-3 py-2 border border-slate-300 rounded-md bg-white">
                                <option>VIP</option>
                                <option>Class A</option>
                            </select>
                        </div>
                        <div class="w-1/2">
                            <label class="block text-sm font-medium text-slate-700 mb-1">تاريخ الانتهاء</label>
                            <input type="date" class="w-full px-3 py-2 border border-slate-300 rounded-md text-slate-600">
                        </div>
                    </div>
                </div>
            </div>
        </section>

        <section>
            <h3 class="text-xs font-bold text-slate-400 uppercase mb-4 border-b pb-2">3. البيانات والجداول (Data Tables)</h3>
            <p class="text-sm text-slate-500 mb-4">لاحظ: الجدول يتحول إلى بطاقات (Cards) عند تصغير الشاشة.</p>
            
            <div class="bg-white rounded-md border border-slate-200 overflow-hidden shadow-sm">
                <div class="hidden md:block overflow-x-auto">
                    <table class="w-full text-right text-sm">
                        <thead class="bg-slate-50 text-slate-500 font-semibold border-b border-slate-200">
                            <tr>
                                <th class="px-6 py-3">المستشفى</th>
                                <th class="px-6 py-3">المدينة</th>
                                <th class="px-6 py-3">الفئة المقبولة</th>
                                <th class="px-6 py-3">نسبة التحمل</th>
                                <th class="px-6 py-3">الحالة</th>
                            </tr>
                        </thead>
                        <tbody class="divide-y divide-slate-100">
                            <tr class="hover:bg-brand-50/30 transition">
                                <td class="px-6 py-4 font-medium text-slate-800">مستشفى د. سليمان فقيه</td>
                                <td class="px-6 py-4 text-slate-600">جدة</td>
                                <td class="px-6 py-4"><span class="px-2 py-1 bg-brand-50 text-brand-700 border border-brand-100 rounded text-xs font-bold">VIP, A</span></td>
                                <td class="px-6 py-4">0%</td>
                                <td class="px-6 py-4"><span class="flex items-center gap-1 text-green-600 text-xs font-bold"><span class="w-2 h-2 rounded-full bg-green-500"></span> معتمد</span></td>
                            </tr>
                            <tr class="hover:bg-brand-50/30 transition">
                                <td class="px-6 py-4 font-medium text-slate-800">مستشفى المواساة</td>
                                <td class="px-6 py-4 text-slate-600">الرياض</td>
                                <td class="px-6 py-4"><span class="px-2 py-1 bg-slate-100 text-slate-600 border border-slate-200 rounded text-xs font-bold">All Classes</span></td>
                                <td class="px-6 py-4">10%</td>
                                <td class="px-6 py-4"><span class="flex items-center gap-1 text-green-600 text-xs font-bold"><span class="w-2 h-2 rounded-full bg-green-500"></span> معتمد</span></td>
                            </tr>
                        </tbody>
                    </table>
                </div>

                <div class="md:hidden bg-slate-50 p-4 space-y-3">
                    <div class="bg-white p-4 rounded-lg shadow-sm border border-slate-200">
                        <div class="flex justify-between items-start mb-2">
                            <h4 class="font-bold text-slate-800">مستشفى د. سليمان فقيه</h4>
                            <span class="text-green-600 text-xs bg-green-50 px-2 py-1 rounded border border-green-100">معتمد</span>
                        </div>
                        <div class="text-sm text-slate-500 mb-3">جدة • VIP, A</div>
                        <div class="flex justify-between items-center pt-3 border-t border-slate-100">
                            <span class="text-xs text-slate-400">نسبة التحمل</span>
                            <span class="font-bold text-slate-800">0%</span>
                        </div>
                    </div>
                    
                    <div class="bg-white p-4 rounded-lg shadow-sm border border-slate-200">
                        <div class="flex justify-between items-start mb-2">
                            <h4 class="font-bold text-slate-800">مستشفى المواساة</h4>
                            <span class="text-green-600 text-xs bg-green-50 px-2 py-1 rounded border border-green-100">معتمد</span>
                        </div>
                        <div class="text-sm text-slate-500 mb-3">الرياض • All Classes</div>
                        <div class="flex justify-between items-center pt-3 border-t border-slate-100">
                            <span class="text-xs text-slate-400">نسبة التحمل</span>
                            <span class="font-bold text-slate-800">10%</span>
                        </div>
                    </div>
                </div>
            </div>
        </section>

        <section x-data="{ openDrawer: false }">
            <h3 class="text-xs font-bold text-slate-400 uppercase mb-4 border-b pb-2">4. أنماط متقدمة (Advanced UX)</h3>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                
                <div class="bg-white p-6 rounded-md border border-slate-200">
                    <h4 class="font-bold text-slate-800 mb-2">رفع الملفات (Bulk Upload)</h4>
                    <div class="border-2 border-dashed border-slate-300 rounded-lg h-40 flex flex-col items-center justify-center text-center hover:bg-brand-50 hover:border-brand-400 transition cursor-pointer group">
                        <div class="p-3 bg-slate-50 rounded-full mb-2 group-hover:bg-white group-hover:text-brand-600 transition">
                            <i class="ph-duotone ph-upload-simple text-2xl text-slate-400 group-hover:text-brand-500"></i>
                        </div>
                        <p class="text-slate-700 text-sm font-medium">اضغط لرفع ملف Excel</p>
                    </div>
                </div>

                <div class="bg-white p-6 rounded-md border border-slate-200 flex flex-col justify-center items-center">
                    <h4 class="font-bold text-slate-800 mb-2">القوائم المنزلقة (Drawers)</h4>
                    <p class="text-sm text-slate-500 mb-4 text-center">تستخدم لتعديل البيانات دون مغادرة الجدول</p>
                    <button @click="openDrawer = true" class="px-6 py-2 bg-slate-800 text-white rounded-md hover:bg-slate-700 shadow-lg flex items-center gap-2">
                        <i class="ph-duotone ph-sidebar"></i> فتح الدرج الجانبي
                    </button>
                </div>

            </div>

            <div class="relative z-50" aria-labelledby="slide-over-title" role="dialog" aria-modal="true" x-show="openDrawer" x-cloak>
                <div class="fixed inset-0 bg-slate-900/50 backdrop-blur-sm transition-opacity" x-show="openDrawer" x-transition.opacity></div>
                <div class="fixed inset-0 overflow-hidden">
                    <div class="absolute inset-0 overflow-hidden">
                        <div class="pointer-events-none fixed inset-y-0 left-0 flex max-w-full pr-10">
                            <div class="pointer-events-auto relative w-screen max-w-md"
                                 x-show="openDrawer"
                                 x-transition:enter="transform transition ease-in-out duration-300"
                                 x-transition:enter-start="-translate-x-full"
                                 x-transition:enter-end="translate-x-0"
                                 x-transition:leave="transform transition ease-in-out duration-300"
                                 x-transition:leave-start="translate-x-0"
                                 x-transition:leave-end="-translate-x-full">
                                
                                <div class="flex h-full flex-col overflow-y-scroll bg-white shadow-xl">
                                    <div class="px-4 py-6 bg-slate-50 border-b border-slate-200 flex justify-between items-center">
                                        <h2 class="text-lg font-bold text-slate-900">تعديل الموظف</h2>
                                        <button @click="openDrawer = false" class="text-slate-400 hover:text-slate-500"><i class="ph-bold ph-x text-xl"></i></button>
                                    </div>
                                    <div class="relative mt-6 flex-1 px-4 sm:px-6 space-y-4">
                                        <div>
                                            <label class="block text-sm font-medium text-slate-700">رقم البوليصة</label>
                                            <input type="text" value="POL-8822" class="mt-1 w-full px-3 py-2 border border-slate-300 rounded-md bg-slate-100" disabled>
                                        </div>
                                        <div>
                                            <label class="block text-sm font-medium text-slate-700">شبكة المستشفيات</label>
                                            <select class="mt-1 w-full px-3 py-2 border border-slate-300 rounded-md">
                                                <option>Network A (Premium)</option>
                                                <option>Network B (Standard)</option>
                                            </select>
                                        </div>
                                    </div>
                                    <div class="flex flex-shrink-0 justify-end px-4 py-4 bg-slate-50 border-t border-slate-200 gap-3">
                                        <button @click="openDrawer = false" class="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 shadow-sm hover:bg-slate-50">إلغاء</button>
                                        <button class="rounded-md border border-transparent bg-brand-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-brand-700">حفظ</button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </section>

    </div>
</body>
</html>




##### this is the UI Example: #####

<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>نظام الوسيط - دليل التصميم</title>
    
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Almarai:wght@300;400;700;800&display=swap" rel="stylesheet">
    
    <script src="https://unpkg.com/@phosphor-icons/web"></script>

    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {
            theme: {
                extend: {
                    fontFamily: {
                        sans: ['Almarai', 'sans-serif'],
                    },
                    colors: {
                        brand: {
                            50: '#f0fdfa',
                            100: '#ccfbf1',
                            500: '#14b8a6', // Teal 500
                            600: '#0d9488', // Teal 600 (Primary)
                            700: '#0f766e',
                            900: '#134e4a',
                        }
                    }
                }
            }
        }
    </script>
    <script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js"></script>

    <style>
        /* Custom Utilities */
        .glass-panel { background: white; border: 1px solid #e2e8f0; }
        [x-cloak] { display: none !important; }
    </style>
</head>
<body class="bg-slate-50 text-slate-800 font-sans antialiased">

    <div class="flex h-screen overflow-hidden" x-data="{ sidebarOpen: true, drawerOpen: false }">
        
        <aside class="bg-slate-900 text-white transition-all duration-300 flex flex-col z-20"
               :class="sidebarOpen ? 'w-64' : 'w-20'">
            <div class="h-16 flex items-center justify-center border-b border-slate-800">
                <i class="ph-duotone ph-shield-check text-3xl text-brand-500"></i>
                <span class="mr-3 font-bold text-lg" x-show="sidebarOpen">وسيط كير</span>
            </div>
            
            <nav class="flex-1 py-6 space-y-1">
                <a href="#" class="flex items-center px-4 py-3 bg-brand-600 border-r-4 border-brand-100">
                    <i class="ph-duotone ph-users-three text-xl"></i>
                    <span class="mr-3" x-show="sidebarOpen">الموظفين والوثائق</span>
                </a>
                <a href="#" class="flex items-center px-4 py-3 text-slate-400 hover:bg-slate-800 hover:text-white transition">
                    <i class="ph-duotone ph-buildings text-xl"></i>
                    <span class="mr-3" x-show="sidebarOpen">شركات التأمين</span>
                </a>
                <a href="#" class="flex items-center px-4 py-3 text-slate-400 hover:bg-slate-800 hover:text-white transition">
                    <i class="ph-duotone ph-first-aid text-xl"></i>
                    <span class="mr-3" x-show="sidebarOpen">المنافع الطبية</span>
                </a>
            </nav>

            <div class="p-4 border-t border-slate-800">
                <button @click="sidebarOpen = !sidebarOpen" class="w-full flex items-center justify-center p-2 rounded hover:bg-slate-800 text-slate-400">
                    <i class="ph-duotone" :class="sidebarOpen ? 'ph-caret-double-right' : 'ph-caret-double-left'"></i>
                </button>
            </div>
        </aside>

        <main class="flex-1 flex flex-col h-full overflow-hidden relative">
            
            <header class="h-16 bg-white border-b border-slate-200 flex items-center justify-between px-6 z-10">
                <h1 class="text-xl font-bold text-slate-800">إدارة وثائق الموظفين</h1>
                
                <div x-data="{ show: true }" x-show="show" class="absolute top-4 left-1/2 transform -translate-x-1/2 bg-slate-800 text-white px-4 py-2 rounded-full shadow-lg flex items-center text-sm z-50">
                    <i class="ph-fill ph-check-circle text-brand-500 ml-2"></i>
                    تم حفظ البيانات بنجاح
                    <button @click="show = false" class="mr-4 hover:text-slate-300"><i class="ph-bold ph-x"></i></button>
                </div>

                <div class="flex items-center space-x-4 space-x-reverse">
                    <div class="relative">
                        <i class="ph-duotone ph-bell text-2xl text-slate-500"></i>
                        <span class="absolute top-0 right-0 h-2 w-2 bg-red-500 rounded-full"></span>
                    </div>
                    <div class="h-8 w-8 rounded-full bg-brand-100 flex items-center justify-center text-brand-700 font-bold border border-brand-200">
                        م.أ
                    </div>
                </div>
            </header>

            <div class="flex-1 overflow-auto p-6 space-y-8">

                <section class="grid grid-cols-1 md:grid-cols-4 gap-4">
                    <div class="bg-white p-4 rounded-md border border-slate-200">
                        <div class="flex justify-between items-start">
                            <div>
                                <p class="text-xs text-slate-500 font-bold uppercase">إجمالي الوثائق</p>
                                <h3 class="text-2xl font-bold text-slate-800 mt-1">1,240</h3>
                            </div>
                            <div class="p-2 bg-brand-50 rounded-md text-brand-600">
                                <i class="ph-duotone ph-file-text text-xl"></i>
                            </div>
                        </div>
                    </div>
                    <div class="bg-white p-4 rounded-md border border-slate-200">
                        <div class="flex justify-between items-start">
                            <div>
                                <p class="text-xs text-slate-500 font-bold uppercase">المطالبات المعلقة</p>
                                <h3 class="text-2xl font-bold text-slate-800 mt-1">34</h3>
                            </div>
                            <div class="p-2 bg-orange-50 rounded-md text-orange-600">
                                <i class="ph-duotone ph-clock text-xl"></i>
                            </div>
                        </div>
                    </div>
                </section>

                <section class="bg-white rounded-md border border-slate-200 overflow-hidden">
                    <div class="p-4 border-b border-slate-200 flex flex-wrap gap-4 justify-between items-center bg-slate-50">
                        <div class="flex items-center gap-2">
                            <div class="relative">
                                <i class="ph-duotone ph-magnifying-glass absolute top-2.5 right-3 text-slate-400"></i>
                                <input type="text" placeholder="بحث باسم الموظف..." class="pl-4 pr-10 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-brand-500 w-64 text-sm">
                            </div>
                            <button @click="drawerOpen = true" class="px-4 py-2 bg-white border border-slate-300 rounded-md text-slate-600 hover:bg-slate-50 text-sm flex items-center gap-2">
                                <i class="ph-duotone ph-funnel"></i>
                                تصفية متقدمة
                            </button>
                        </div>
                        <button class="px-4 py-2 bg-brand-600 text-white rounded-md hover:bg-brand-700 text-sm flex items-center gap-2 shadow-sm">
                            <i class="ph-bold ph-plus"></i>
                            إضافة وثيقة
                        </button>
                    </div>

                    <div class="hidden md:block overflow-x-auto">
                        <table class="w-full text-right text-sm">
                            <thead class="bg-slate-50 text-slate-500 font-semibold border-b border-slate-200">
                                <tr>
                                    <th class="px-6 py-3">الموظف</th>
                                    <th class="px-6 py-3">رقم الوثيقة</th>
                                    <th class="px-6 py-3">الفئة</th>
                                    <th class="px-6 py-3">الحالة</th>
                                    <th class="px-6 py-3">نسبة التحمل</th>
                                    <th class="px-6 py-3 w-20"></th>
                                </tr>
                            </thead>
                            <tbody class="divide-y divide-slate-100">
                                <tr class="hover:bg-slate-50 group transition-colors">
                                    <td class="px-6 py-4 font-medium text-slate-800">محمد عبدالله الغامدي</td>
                                    <td class="px-6 py-4 text-slate-500 font-mono">POL-2024-889</td>
                                    <td class="px-6 py-4"><span class="px-2 py-1 bg-purple-50 text-purple-700 rounded text-xs font-bold border border-purple-100">VIP</span></td>
                                    <td class="px-6 py-4"><span class="flex items-center gap-1 text-green-600"><span class="w-2 h-2 rounded-full bg-green-500"></span> سارية</span></td>
                                    <td class="px-6 py-4 text-slate-600">0%</td>
                                    <td class="px-6 py-4 text-left">
                                        <div class="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                                            <button class="p-1 hover:text-brand-600" title="تعديل"><i class="ph-duotone ph-pencil-simple text-lg"></i></button>
                                            <button class="p-1 hover:text-red-600" title="حذف"><i class="ph-duotone ph-trash text-lg"></i></button>
                                        </div>
                                    </td>
                                </tr>
                                <tr class="hover:bg-slate-50 group transition-colors">
                                    <td class="px-6 py-4 font-medium text-slate-800">سارة أحمد علي</td>
                                    <td class="px-6 py-4 text-slate-500 font-mono">POL-2024-902</td>
                                    <td class="px-6 py-4"><span class="px-2 py-1 bg-blue-50 text-blue-700 rounded text-xs font-bold border border-blue-100">Class A</span></td>
                                    <td class="px-6 py-4"><span class="flex items-center gap-1 text-red-600"><span class="w-2 h-2 rounded-full bg-red-500"></span> منتهية</span></td>
                                    <td class="px-6 py-4 text-slate-600">10%</td>
                                    <td class="px-6 py-4 text-left">
                                        <div class="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                                            <button class="p-1 hover:text-brand-600"><i class="ph-duotone ph-pencil-simple text-lg"></i></button>
                                            <button class="p-1 hover:text-red-600"><i class="ph-duotone ph-trash text-lg"></i></button>
                                        </div>
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                    </div>

                    <div class="md:hidden p-4 space-y-4 bg-slate-50">
                        <div class="bg-white p-4 rounded-md shadow-sm border border-slate-200">
                            <div class="flex justify-between items-start mb-3">
                                <div>
                                    <h4 class="font-bold text-slate-800">محمد عبدالله الغامدي</h4>
                                    <p class="text-xs text-slate-500 mt-1">POL-2024-889</p>
                                </div>
                                <span class="px-2 py-1 bg-purple-50 text-purple-700 rounded text-xs font-bold border border-purple-100">VIP</span>
                            </div>
                            <div class="grid grid-cols-2 gap-2 text-sm text-slate-600 mb-3">
                                <div class="flex flex-col"><span class="text-xs text-slate-400">الحالة</span> <span class="text-green-600 font-bold">سارية</span></div>
                                <div class="flex flex-col"><span class="text-xs text-slate-400">التحمل</span> <span>0%</span></div>
                            </div>
                            <div class="pt-3 border-t border-slate-100 flex justify-end gap-3">
                                <button class="text-brand-600 text-sm font-medium">تعديل</button>
                                <button class="text-red-600 text-sm font-medium">حذف</button>
                            </div>
                        </div>
                        
                        <div class="bg-white p-4 rounded-md shadow-sm border border-slate-200">
                             <div class="flex justify-between items-start mb-3">
                                <div>
                                    <h4 class="font-bold text-slate-800">سارة أحمد علي</h4>
                                    <p class="text-xs text-slate-500 mt-1">POL-2024-902</p>
                                </div>
                                <span class="px-2 py-1 bg-blue-50 text-blue-700 rounded text-xs font-bold border border-blue-100">Class A</span>
                            </div>
                            <div class="grid grid-cols-2 gap-2 text-sm text-slate-600 mb-3">
                                <div class="flex flex-col"><span class="text-xs text-slate-400">الحالة</span> <span class="text-red-600 font-bold">منتهية</span></div>
                                <div class="flex flex-col"><span class="text-xs text-slate-400">التحمل</span> <span>10%</span></div>
                            </div>
                            <div class="pt-3 border-t border-slate-100 flex justify-end gap-3">
                                <button class="text-brand-600 text-sm font-medium">تعديل</button>
                                <button class="text-red-600 text-sm font-medium">حذف</button>
                            </div>
                        </div>
                    </div>
                </section>

                <section class="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div class="bg-white p-6 rounded-md border border-slate-200">
                        <h3 class="font-bold text-slate-800 mb-4">رفع ملف المطالبات</h3>
                        <div class="border-2 border-dashed border-slate-300 rounded-lg p-8 flex flex-col items-center justify-center text-center hover:bg-slate-50 hover:border-brand-400 transition cursor-pointer">
                            <i class="ph-duotone ph-cloud-arrow-up text-4xl text-brand-500 mb-3"></i>
                            <p class="text-slate-700 font-medium">اسحب ملف Excel هنا أو اضغط للاستعراض</p>
                            <p class="text-slate-400 text-sm mt-1">الحد الأقصى 10MB</p>
                        </div>
                    </div>

                    <div class="bg-white p-6 rounded-md border border-slate-200">
                        <h3 class="font-bold text-slate-800 mb-4">حالة النظام (Empty State Demo)</h3>
                        <div class="text-center py-8">
                            <div class="inline-flex items-center justify-center w-16 h-16 bg-slate-100 rounded-full mb-4">
                                <i class="ph-duotone ph-users text-3xl text-slate-400"></i>
                            </div>
                            <h4 class="text-slate-800 font-bold mb-1">لا توجد شركات معرفة</h4>
                            <p class="text-slate-500 text-sm mb-4">ابدأ بإضافة أول شركة متعاقدة للنظام</p>
                            <button class="px-4 py-2 bg-brand-600 text-white rounded-md hover:bg-brand-700 text-sm">
                                إضافة شركة جديدة
                            </button>
                        </div>
                    </div>
                </section>
                
            </div>
        </main>

        <div class="fixed inset-0 z-50 overflow-hidden" x-show="drawerOpen" style="display: none;" x-transition.opacity>
            <div class="absolute inset-0 bg-slate-900/50 backdrop-blur-sm" @click="drawerOpen = false"></div>
            
            <div class="absolute inset-y-0 left-0 max-w-md w-full flex bg-white shadow-2xl transform transition-transform duration-300 ease-in-out"
                 x-show="drawerOpen"
                 x-transition:enter="transform transition ease-in-out duration-300"
                 x-transition:enter-start="-translate-x-full"
                 x-transition:enter-end="translate-x-0"
                 x-transition:leave="transform transition ease-in-out duration-300"
                 x-transition:leave-start="translate-x-0"
                 x-transition:leave-end="-translate-x-full">
                
                <div class="w-full flex flex-col h-full">
                    <div class="px-6 py-4 border-b border-slate-200 flex justify-between items-center bg-slate-50">
                        <h2 class="text-lg font-bold text-slate-800">تصفية البيانات</h2>
                        <button @click="drawerOpen = false" class="text-slate-400 hover:text-slate-600"><i class="ph-bold ph-x text-xl"></i></button>
                    </div>
                    
                    <div class="flex-1 overflow-y-auto p-6 space-y-6">
                        <div>
                            <label class="block text-sm font-medium text-slate-700 mb-1">الفئة التأمينية</label>
                            <select class="w-full px-3 py-2 border border-slate-300 rounded-md bg-white focus:outline-none focus:ring-1 focus:ring-brand-500">
                                <option>الكل</option>
                                <option>VIP</option>
                                <option>Class A</option>
                            </select>
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-slate-700 mb-1">نطاق تاريخ الانتهاء</label>
                            <div class="grid grid-cols-2 gap-2">
                                <input type="date" class="w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-brand-500 text-slate-600">
                                <input type="date" class="w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-brand-500 text-slate-600">
                            </div>
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-slate-700 mb-1">المدينة</label>
                            <input type="text" placeholder="مثال: الرياض" class="w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-brand-500">
                        </div>
                    </div>

                    <div class="p-6 border-t border-slate-200 bg-slate-50 flex gap-3">
                        <button class="flex-1 bg-brand-600 text-white py-2 rounded-md font-medium hover:bg-brand-700">تطبيق</button>
                        <button @click="drawerOpen = false" class="flex-1 bg-white border border-slate-300 text-slate-700 py-2 rounded-md font-medium hover:bg-slate-50">إلغاء</button>
                    </div>
                </div>
            </div>
        </div>

    </div>

</body>
</html>