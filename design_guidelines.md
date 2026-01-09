{
  "project": "ABS Contract Admin Agent",
  "app_type": "Legal-tech AI chat + contract analysis",
  "audience": ["In-house counsel", "Law firm associates/partners", "Contract managers", "Ops/Procurement"],
  "brand_personality": ["trustworthy", "precise", "audit-ready", "efficient", "calm"],
  "success_actions": [
    "User uploads contract (drag/drop or select)",
    "User chats with agent; messages stream reliably",
    "Outputs available in tabs: JSON (monospace viewer) and Markdown (rendered)",
    "Clear history switcher on sidebar with search and pinned threads",
    "Responsive and keyboard accessible with test IDs on all key elements"
  ],

  "typography": {
    "primary": {
      "family": "Inter",
      "import": "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap",
      "usage": ["all UI", "headings", "buttons"],
      "tracking": {"heading": "tracking-tight", "body": "tracking-normal"}
    },
    "mono": {
      "family": "Source Code Pro",
      "import": "https://fonts.googleapis.com/css2?family=Source+Code+Pro:wght@400;500;600&display=swap",
      "usage": ["JSON viewer", "inline code", "diff blocks"]
    },
    "scale": {
      "h1": "text-4xl sm:text-5xl lg:text-6xl font-semibold leading-tight",
      "h2": "text-base sm:text-lg font-semibold text-foreground/90",
      "h3": "text-base font-medium",
      "body": "text-base sm:text-sm text-foreground/90",
      "small": "text-sm text-muted-foreground"
    }
  },

  "color_system": {
    "notes": "Trusted navy/blue with neutral surfaces. Avoid purple entirely.",
    "tokens_hsl": {
      "--brand-navy": "216 35% 18%",       
      "--brand-blue": "210 90% 40%",       
      "--brand-azure": "204 94% 55%",      
      "--brand-soft-blue": "210 40% 96%",   
      "--brand-teal": "187 40% 40%",       
      "--success": "158 64% 42%",
      "--warning": "35 96% 45%",
      "--error": "356 72% 46%",
      "--neutral-50": "0 0% 98%",
      "--neutral-100": "210 20% 98%",
      "--neutral-200": "220 14% 96%",
      "--neutral-300": "220 13% 91%",
      "--neutral-400": "215 16% 47%",
      "--neutral-900": "224 71% 4%"
    },
    "tailwind_mapping": {
      "primary": "hsl(var(--brand-blue))",
      "ring": "hsl(var(--brand-azure))",
      "background": "hsl(var(--neutral-100))",
      "foreground": "hsl(224 71% 4%)",
      "card": "hsl(var(--neutral-50))",
      "accent": "hsl(var(--brand-soft-blue))"
    },
    "contrast_rules": [
      "Buttons/links must meet WCAG AA (contrast >= 4.5:1)",
      "Never place text directly on saturated gradient; use overlay or solid surface"
    ]
  },

  "gradients_and_texture": {
    "restriction": "Never exceed 20% viewport; no purple/pink/green-blue heavy gradients; never on text-heavy blocks.",
    "allowed_use": ["top header accent bar", "section separators", "decorative background stripes"],
    "examples": [
      {
        "name": "Calm Ocean Header",
        "css": "bg-[linear-gradient(120deg,theme(colors.blue.50),theme(colors.blue.100),theme(colors.teal.50))]",
        "usage": "Apply to header wrapper only with inner cards on solid backgrounds"
      }
    ],
    "texture": "Optional subtle noise overlay at 4–6% opacity on large empty surfaces"
  },

  "layout": {
    "pattern": "Desktop-first split with resizable left sidebar + main chat + right output tabs (collapsible on mobile).",
    "grid": {
      "sidebar": {"width": "280px", "min": "240px", "max": "360px"},
      "content": {"max_width": "1280px", "padding": "px-3 sm:px-4 lg:px-6"}
    },
    "skeleton": {
      "header": "Sticky top bar: logo left, global search, actions (Upload, New Chat)",
      "body": "ResizablePanelGroup horizontally: left History, center Chat, right Output Tabs (optional hide)",
      "footer": "Compact legal footer (links)"
    },
    "mobile": {
      "behavior": [
        "Sidebar collapses behind Sheet",
        "Tabs switch for Chat/Output; upload as full-width Card at top"
      ]
    }
  },

  "components": {
    "from_shadcn": [
      "accordion.jsx", "alert.jsx", "alert-dialog.jsx", "avatar.jsx", "badge.jsx", "button.jsx", "card.jsx",
      "checkbox.jsx", "command.jsx", "dialog.jsx", "drawer.jsx", "dropdown-menu.jsx", "form.jsx", "input.jsx",
      "label.jsx", "menubar.jsx", "popover.jsx", "progress.jsx", "resizable.jsx", "scroll-area.jsx", 
      "select.jsx", "separator.jsx", "sheet.jsx", "skeleton.jsx", "switch.jsx", "table.jsx", "tabs.jsx", 
      "textarea.jsx", "tooltip.jsx", "sonner.jsx"
    ],
    "composite_patterns": [
      {
        "name": "FileUploadZone",
        "built_with": ["card.jsx", "button.jsx", "progress.jsx", "tooltip.jsx"],
        "lib": "react-dropzone (for drag & drop)",
        "states": ["idle", "drag-active", "uploading", "error", "complete"],
        "accessibility": ["role=button", "aria-label=\"Upload contracts\"", "keyboard: Enter/Space triggers file dialog"],
        "testids": ["file-upload-zone", "file-upload-input", "file-upload-progress"]
      },
      {
        "name": "ChatComposer",
        "built_with": ["textarea.jsx", "button.jsx", "tooltip.jsx", "popover.jsx"],
        "features": ["Shift+Enter newline", "Enter to send", "Attach button", "disabled while uploading"],
        "testids": ["chat-input-textarea", "chat-send-button", "chat-attach-button"]
      },
      {
        "name": "HistoryList",
        "built_with": ["scroll-area.jsx", "button.jsx", "command.jsx", "separator.jsx"],
        "features": ["search", "pin", "context menu (rename/delete)", "badges for active model"],
        "testids": ["history-search-input", "history-item-button"]
      },
      {
        "name": "OutputTabs",
        "built_with": ["tabs.jsx", "scroll-area.jsx", "card.jsx"],
        "tabs": ["json", "markdown"],
        "testids": ["output-tab-json", "output-tab-markdown"]
      }
    ]
  },

  "tokens_css": {
    "place_into": "/app/frontend/src/index.css :root",
    "snippet": ":root{ --brand-navy: 216 35% 18%; --brand-blue: 210 90% 40%; --brand-azure: 204 94% 55%; --brand-soft-blue: 210 40% 96%; --brand-teal: 187 40% 40%; --success: 158 64% 42%; --warning: 35 96% 45%; --error: 356 72% 46%; } .btn-focus{ outline:2px solid hsl(var(--brand-azure)); outline-offset:2px }"
  },

  "micro_interactions": {
    "principles": [
      "No transition: all; limit to colors/opacities",
      "Buttons: color, shadow, and scale(0.98) on active",
      "Message bubbles: 60–120ms fade/slide with spring-y=0.75",
      "Skeletons for async states; Progress for uploads",
      "Subtle ScrollArea shadow gradients at edges"
    ],
    "framer_motion": {
      "install": "npm i framer-motion",
      "usage": "AnimatePresence for streaming messages; motion.div for message row fade-in"
    }
  },

  "additional_libraries": [
    {
      "name": "react-dropzone",
      "install": "npm i react-dropzone",
      "usage": "Build accessible drag-and-drop on top of shadcn Card; provide input[type=file] fallback"
    },
    {
      "name": "react-json-view-lite",
      "install": "npm i react-json-view-lite",
      "usage": "Lightweight JSON viewer in the JSON tab using mono font"
    },
    {
      "name": "react-markdown + remark-gfm",
      "install": "npm i react-markdown remark-gfm",
      "usage": "Render Markdown output tab with tables and checklists"
    },
    {
      "name": "lucide-react",
      "install": "npm i lucide-react",
      "usage": "Icons: Upload, Send, Paperclip, Search, Trash, Pin"
    }
  ],

  "accessibility": {
    "keyboard": ["Tab/Shift+Tab cycles focus", "Esc closes dialogs/sheets", "Enter sends message", "Cmd/Ctrl+K focuses Command palette"],
    "aria": ["role=search on history search", "aria-live=polite for streaming assistant messages", "aria-busy while uploading"],
    "contrast": "All actionable elements AA compliant; verify dark text on soft-blue surfaces"
  },

  "responsive_rules": {
    "mobile": [
      "Header becomes 56px with condensed actions",
      "Sidebar hidden in Sheet; button in header toggles",
      "Composer fixed to bottom with safe-area insets"
    ],
    "tablet": ["Sidebar 240px; output panel collapsible"],
    "desktop": ["Three-panel layout default"]
  },

  "testing_ids": {
    "convention": "kebab-case, describe role (not style)",
    "examples": [
      "data-testid=\"file-upload-zone\"",
      "data-testid=\"chat-send-button\"",
      "data-testid=\"history-item-button\"",
      "data-testid=\"output-tab-json\"",
      "data-testid=\"assistant-message\"",
      "data-testid=\"error-toast\""
    ]
  },

  "code_scaffolds": {
    "app_shell": {
      "file": "/app/frontend/src/App.js",
      "notes": "JS files only; use named exports for components; paths point to /src/components/ui/*.jsx",
      "snippet": "import React from 'react';\nimport { ResizablePanelGroup, ResizablePanel, ResizableHandle } from './components/ui/resizable';\nimport { ScrollArea } from './components/ui/scroll-area';\nimport { Tabs, TabsList, TabsTrigger, TabsContent } from './components/ui/tabs';\nimport { Button } from './components/ui/button';\nimport { Card } from './components/ui/card';\nimport { Textarea } from './components/ui/textarea';\nimport { Input } from './components/ui/input';\nimport { Separator } from './components/ui/separator';\nimport { Toaster } from './components/ui/sonner';\nimport { Tooltip, TooltipContent, TooltipTrigger, TooltipProvider } from './components/ui/tooltip';\nimport { Sheet, SheetContent, SheetTrigger } from './components/ui/sheet';\nimport { Search, Send, Upload, Paperclip, Menu } from 'lucide-react';\n\nexport default function App(){\n  return (\n    <div className=\"min-h-screen bg-background text-foreground\">\n      <header className=\"sticky top-0 z-40 border-b bg-white/70 backdrop-blur supports-[backdrop-filter]:bg-white/60\">\n        <div className=\"mx-auto max-w-[1400px] px-3 sm:px-4 lg:px-6 h-16 flex items-center gap-3\">\n          <Sheet>\n            <SheetTrigger asChild>\n              <Button variant=\"ghost\" size=\"icon\" className=\"lg:hidden\" data-testid=\"open-sidebar-button\">\n                <Menu className=\"h-5 w-5\" />\n              </Button>\n            </SheetTrigger>\n            <SheetContent side=\"left\" className=\"p-0 w-[300px]\">\n              <Sidebar />\n            </SheetContent>\n          </Sheet>\n          <div className=\"font-semibold text-lg text-slate-900\">ABS Contract Admin</div>\n          <div className=\"ml-auto hidden md:flex items-center gap-2\">\n            <div className=\"relative\">\n              <Search className=\"absolute left-2 top-2.5 h-4 w-4 text-muted-foreground\" />\n              <Input data-testid=\"global-search-input\" placeholder=\"Search history\" className=\"pl-8 w-64\" />\n            </div>\n            <Button data-testid=\"new-chat-button\" className=\"bg-[hsl(var(--brand-blue))] hover:bg-[hsl(var(--brand-azure))]\">New Chat</Button>\n            <Button data-testid=\"open-upload-button\" variant=\"outline\"><Upload className=\"h-4 w-4 mr-2\" />Upload</Button>\n          </div>\n        </div>\n      </header>\n\n      <main className=\"mx-auto max-w-[1400px] px-3 sm:px-4 lg:px-6\">\n        <ResizablePanelGroup direction=\"horizontal\" className=\"mt-4 rounded-lg border\">\n          <ResizablePanel defaultSize={22} minSize={18} maxSize={30} className=\"hidden lg:block\">\n            <Sidebar />\n          </ResizablePanel>\n          <ResizableHandle withHandle />\n          <ResizablePanel defaultSize={48} minSize={34}>\n            <ChatArea />\n          </ResizablePanel>\n          <ResizableHandle withHandle />\n          <ResizablePanel defaultSize={30} minSize={24}>\n            <OutputTabs />\n          </ResizablePanel>\n        </ResizablePanelGroup>\n      </main>\n      <Toaster />\n    </div>\n  );\n}\n\nexport const Sidebar = () => (\n  <div className=\"h-full flex flex-col\">\n    <div className=\"p-3 border-b\">\n      <Input data-testid=\"history-search-input\" placeholder=\"Search...\" />\n    </div>\n    <ScrollArea className=\"flex-1\">\n      <nav className=\"p-2 space-y-1\">\n        {[...Array(8)].map((_,i)=> (\n          <Button key={i} variant=\"ghost\" className=\"w-full justify-start text-left\" data-testid=\"history-item-button\">\n            Q{`#${i+1}`} · NDA Review\n          </Button>\n        ))}\n      </nav>\n    </ScrollArea>\n    <div className=\"p-2 border-t\">\n      <Button variant=\"outline\" className=\"w-full\" data-testid=\"new-folder-button\">New Folder</Button>\n    </div>\n  </div>\n);\n\nexport const ChatArea = () => (\n  <div className=\"h-full flex flex-col\">\n    <ScrollArea className=\"flex-1 p-4\">\n      <div className=\"space-y-4\">\n        <AssistantMessage />\n      </div>\n    </ScrollArea>\n    <Separator />\n    <div className=\"p-3\">\n      <Card className=\"p-2\">\n        <div className=\"flex items-end gap-2\">\n          <TooltipProvider><Tooltip><TooltipTrigger asChild>\n            <Button variant=\"ghost\" size=\"icon\" data-testid=\"chat-attach-button\"><Paperclip className=\"h-4 w-4\"/></Button>\n          </TooltipTrigger><TooltipContent>Attach</TooltipContent></Tooltip></TooltipProvider>\n          <Textarea data-testid=\"chat-input-textarea\" rows={2} placeholder=\"Ask anything about your contract...\" className=\"resize-none\" />\n          <Button data-testid=\"chat-send-button\" className=\"bg-[hsl(var(--brand-blue))] hover:bg-[hsl(var(--brand-azure))]\"><Send className=\"h-4 w-4 mr-1\"/>Send</Button>\n        </div>\n      </Card>\n    </div>\n  </div>\n);\n\nexport const AssistantMessage = () => (\n  <div className=\"max-w-2xl\" data-testid=\"assistant-message\">\n    <div className=\"text-sm text-muted-foreground mb-1\">Assistant · now</div>\n    <Card className=\"p-3 bg-white\">\n      <p className=\"text-sm\">Upload an agreement to start. I can summarize, extract clauses, and flag risks.</p>\n    </Card>\n  </div>\n);\n\nexport const OutputTabs = () => (\n  <Tabs defaultValue=\"json\" className=\"h-full flex flex-col\">\n    <div className=\"border-b\">\n      <TabsList>\n        <TabsTrigger value=\"json\" data-testid=\"output-tab-json\">JSON</TabsTrigger>\n        <TabsTrigger value=\"markdown\" data-testid=\"output-tab-markdown\">Markdown</TabsTrigger>\n      </TabsList>\n    </div>\n    <TabsContent value=\"json\" className=\"flex-1 m-0\"><ScrollArea className=\"h-[calc(100vh-260px)] p-4 font-mono text-sm\">{/* JSON viewer here */}</ScrollArea></TabsContent>\n    <TabsContent value=\"markdown\" className=\"flex-1 m-0\"><ScrollArea className=\"h-[calc(100vh-260px)] p-4 prose max-w-none\">{/* Markdown renderer here */}</ScrollArea></TabsContent>\n  </Tabs>\n);"
    }
  },

  "motion": {
    "easings": {"enter": "[0.22,1,0.36,1]", "exit": "[0.4,0,1,1]"},
    "durations_ms": {"fast": 120, "base": 180, "slow": 260}
  },

  "image_urls": [
    {
      "url": "https://images.unsplash.com/photo-1731074803846-ac506947040d?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NDQ2MzR8MHwxfHNlYXJjaHwxfHxtaW5pbWFsJTIwbGVnYWwlMjB0ZWNoJTIwYmx1ZSUyMG5hdnklMjBjb250cmFjdCUyMGRvY3VtZW50JTIwZGVzayUyMGFic3RyYWN0JTIwYmFja2dyb3VuZHxlbnwwfHx8fDE3NjQ5NjA2MDR8MA&ixlib=rb-4.1.0&q=85",
      "category": "empty-state background",
      "description": "Close-up text on paper in cool blue tones; use as 10–15% opacity backdrop"
    },
    {
      "url": "https://images.unsplash.com/photo-1669296143651-192ed9c87c22?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NDQ2MzR8MHwxfHNlYXJjaHwyfHxtaW5pbWFsJTIwbGVnYWwlMjB0ZWNoJTIwYmx1ZSUyMG5hdnklMjBjb250cmFjdCUyMGRvY3VtZW50JTIwZGVzayUyMGFic3RyYWN0JTIwYmFja2dyb3VuZHxlbnwwfHx8fDE3NjQ5NjA2MDR8MA&ixlib=rb-4.1.0&q=85",
      "category": "hero/header accent",
      "description": "Abstract blurred legal text, navy-blue palette"
    },
    {
      "url": "https://images.unsplash.com/photo-1745970649913-2edb9dca4f74?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NDQ2MzR8MHwxfHNlYXJjaHwzfHxtaW5pbWFsJTIwbGVnYWwlMjB0ZWNoJTIwYmx1ZSUyMG5hdnklMjBjb250cmFjdCUyMGRvY3VtZW50JTIwZGVzayUyMGFic3RyYWN0JTIwYmFja2dyb3VuZHxlbnwwfHx8fDE3NjQ5NjA2MDR8MA&ixlib=rb-4.1.0&q=85",
      "category": "marketing/empty state card",
      "description": "Minimal certificate on desk; use in onboarding panel"
    }
  ],

  "component_path": {
    "root": "/app/frontend/src/components/ui/",
    "list": {
      "button": "button.jsx",
      "tabs": "tabs.jsx",
      "input": "input.jsx",
      "textarea": "textarea.jsx",
      "card": "card.jsx",
      "scroll-area": "scroll-area.jsx",
      "resizable": "resizable.jsx",
      "sheet": "sheet.jsx",
      "separator": "separator.jsx",
      "tooltip": "tooltip.jsx",
      "sonner": "sonner.jsx",
      "dialog": "dialog.jsx",
      "command": "command.jsx",
      "progress": "progress.jsx",
      "avatar": "avatar.jsx",
      "badge": "badge.jsx"
    }
  },

  "instructions_to_main_agent": [
    "Import Inter and Source Code Pro via <link> in index.html or @import in index.css; set body { font-family: Inter, ... } and .font-mono { font-family: 'Source Code Pro', ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace; }",
    "Update :root in /app/frontend/src/index.css with tokens in tokens_css.snippet (do not remove existing shadcn tokens).",
    "Build the App.js shell from code_scaffolds.app_shell.snippet. Ensure all interactive elements include data-testid attributes.",
    "Compose FileUploadZone using react-dropzone inside Card with dashed border, hover/drag states; use Progress during upload.",
    "Render JSON results in OutputTabs > JSON using react-json-view-lite with theme matching brand (light, blue selection).",
    "Render Markdown results in OutputTabs > Markdown using react-markdown and remark-gfm; wrap in ScrollArea and prose classes.",
    "Use sonner for toasts: success on upload complete, error on parse failure. Path: /app/frontend/src/components/ui/sonner.jsx",
    "No universal transition. Add hover and focus transitions only on color and box-shadow for buttons and links.",
    "Adhere to Gradient Restriction Rule: only soft blue gradient band in header if desired; content surfaces remain solid white or gray.",
    "Ensure keyboard shortcuts: Enter=send, Shift+Enter=newline; Esc closes open menus/dialogs; Cmd/Ctrl+K opens Command palette.",
    "Accessibility: aria-live for assistant responses; aria-busy on upload; focus-visible ring uses --brand-azure.",
    "Testing: Attach data-testid to every control, tab, menu, toast, and critical text (see testing_ids.examples).",
    "Mobile: Hide sidebar into Sheet; keep composer docked to bottom with safe-area; tabs drive content switching.",
    "Icons via lucide-react; NEVER use emoji icons."
  ]
}


<General UI UX Design Guidelines>  
    - You must **not** apply universal transition. Eg: `transition: all`. This results in breaking transforms. Always add transitions for specific interactive elements like button, input excluding transforms
    - You must **not** center align the app container, ie do not add `.App { text-align: center; }` in the css file. This disrupts the human natural reading flow of text
   - NEVER: use AI assistant Emoji characters like`🤖🧠💭💡🔮🎯📚🎭🎬🎪🎉🎊🎁🎀🎂🍰🎈🎨🎰💰💵💳🏦💎🪙💸🤑📊📈📉💹🔢🏆🥇 etc for icons. Always use **FontAwesome cdn** or **lucid-react** library already installed in the package.json

 **GRADIENT RESTRICTION RULE**
NEVER use dark/saturated gradient combos (e.g., purple/pink) on any UI element.  Prohibited gradients: blue-500 to purple 600, purple 500 to pink-500, green-500 to blue-500, red to pink etc
NEVER use dark gradients for logo, testimonial, footer etc
NEVER let gradients cover more than 20% of the viewport.
NEVER apply gradients to text-heavy content or reading areas.
NEVER use gradients on small UI elements (<100px width).
NEVER stack multiple gradient layers in the same viewport.

**ENFORCEMENT RULE:**
    • Id gradient area exceeds 20% of viewport OR affects readability, **THEN** use solid colors

**How and where to use:**
   • Section backgrounds (not content backgrounds)
   • Hero section header content. Eg: dark to light to dark color
   • Decorative overlays and accent elements only
   • Hero section with 2-3 mild color
   • Gradients creation can be done for any angle say horizontal, vertical or diagonal

- For AI chat, voice application, **do not use purple color. Use color like light green, ocean blue, peach orange etc**

</Font Guidelines>

- Every interaction needs micro-animations - hover states, transitions, parallax effects, and entrance animations. Static = dead. 
   
- Use 2-3x more spacing than feels comfortable. Cramped designs look cheap.

- Subtle grain textures, noise overlays, custom cursors, selection states, and loading animations: separates good from extraordinary.
   
- Before generating UI, infer the visual style from the problem statement (palette, contrast, mood, motion) and immediately instantiate it by setting global design tokens (primary, secondary/accent, background, foreground, ring, state colors), rather than relying on any library defaults. Don't make the background dark as a default step, always understand problem first and define colors accordingly
    Eg: - if it implies playful/energetic, choose a colorful scheme
           - if it implies monochrome/minimal, choose a black–white/neutral scheme

**Component Reuse:**
	- Prioritize using pre-existing components from src/components/ui when applicable
	- Create new components that match the style and conventions of existing components when needed
	- Examine existing components to understand the project's component patterns before creating new ones

**IMPORTANT**: Do not use HTML based component like dropdown, calendar, toast etc. You **MUST** always use `/app/frontend/src/components/ui/ ` only as a primary components as these are modern and stylish component

**Best Practices:**
	- Use Shadcn/UI as the primary component library for consistency and accessibility
	- Import path: ./components/[component-name]

**Export Conventions:**
	- Components MUST use named exports (export const ComponentName = ...)
	- Pages MUST use default exports (export default function PageName() {...})

**Toasts:**
  - Use `sonner` for toasts"
  - Sonner component are located in `/app/src/components/ui/sonner.tsx`

Use 2–4 color gradients, subtle textures/noise overlays, or CSS-based noise to avoid flat visuals.
</General UI UX Design Guidelines>"}]},