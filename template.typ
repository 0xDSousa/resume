// ATS-optimized Typst CV template
// Reads cv.yaml directly (compile with: make all)

#let raw_data = yaml("cv.yaml")
#let cv = raw_data.cv
#let photo_path = sys.inputs.at("photo", default: "")
#let theme_mode = sys.inputs.at("theme", default: "light")
#let font_choice = sys.inputs.at("font", default: "Nimbus Sans")

// --- Color Palette (High-Contrast Light + Executive Dark Mode) ---
#let is_dark = theme_mode == "dark"
#let c_bg = if is_dark { rgb("#0f172a") } else { rgb("#ffffff") }
#let c_ink = if is_dark { rgb("#e2e8f0") } else { rgb("#111827") }       // Body text
#let c_dark = if is_dark { rgb("#f8fafc") } else { rgb("#030712") }      // Name, companies, section headers
#let c_sub = if is_dark { rgb("#cbd5e1") } else { rgb("#1f2937") }       // Role titles, degree names
#let c_muted = if is_dark { rgb("#94a3b8") } else { rgb("#374151") }     // Secondary metadata (high readability)
#let c_accent = if is_dark { rgb("#60a5fa") } else { rgb("#1d4ed8") }    // Links, active-role node
#let c_rule = if is_dark { rgb("#334155") } else { rgb("#94a3b8") }      // Section rules, timeline connectors
#let c_pill_bg = if is_dark { rgb("#1e293b") } else { rgb("#e5e7eb") }   // Date pill background
#let c_pill_fg = if is_dark { rgb("#e2e8f0") } else { rgb("#1f2937") }   // Date pill text

// --- Page & Typography (ATS-hardened) ---
#set document(
  title: cv.name + " - CV",
  author: cv.name,
)

#set page(
  paper: "a4",
  fill: c_bg,
  margin: (top: 1.3cm, bottom: 1.3cm, left: 1.55cm, right: 1.55cm),
)

#set text(
  font: (font_choice, "Lato", "Liberation Sans", "Noto Sans"),
  size: 9.4pt,
  fill: c_ink,
  ligatures: false,
  discretionary-ligatures: false,
  hyphenate: false,
  number-type: "lining",
  number-width: "tabular",
)

#set par(
  leading: 0.56em,
  spacing: 0.72em,
  justify: false,
)

#set list(
  indent: 0.55em,
  body-indent: 0.45em,
  spacing: 0.72em,
  tight: false,
  marker: [•],
)

#show link: set text(fill: c_accent, weight: "regular")

#show heading.where(level: 1): set text(size: 20pt, weight: "bold", fill: c_dark)
#show heading.where(level: 1): set block(above: 0pt, below: 0.25em)
#show heading.where(level: 2): set text(size: 10.4pt, weight: "bold", fill: c_dark)
#show heading.where(level: 2): set block(above: 0pt, below: 0.22em)

// --- Helpers ---
#let months = (
  "01": "Jan", "02": "Feb", "03": "Mar", "04": "Apr",
  "05": "May", "06": "Jun", "07": "Jul", "08": "Aug",
  "09": "Sep", "10": "Oct", "11": "Nov", "12": "Dec",
)

#let fmt_date(d) = {
  if d == none { return "" }
  let s = str(d)
  if lower(s) == "present" { return "Present" }
  let parts = s.split("-")
  if parts.len() == 2 and parts.at(1) in months {
    return months.at(parts.at(1)) + " " + parts.at(0)
  }
  return s
}

#let is_present(entry) = {
  "end_date" in entry and entry.end_date != none and lower(str(entry.end_date)) == "present"
}

#let fmt_range(entry) = {
  if "date" in entry and entry.date != none {
    return fmt_date(entry.date)
  }
  let s = if "start_date" in entry { fmt_date(entry.start_date) } else { "" }
  let e = if "end_date" in entry { fmt_date(entry.end_date) } else { "" }
  if s != "" and e != "" {
    return s + " – " + e
  }
  return s + e
}

#let date_badge(dr) = {
  if dr == "" { return [] }
  box(
    fill: c_pill_bg,
    inset: (x: 5.5pt, y: 2pt),
    outset: (y: 0.5pt),
    radius: 3pt,
    baseline: 1pt,
    text(size: 8.3pt, weight: "medium", fill: c_pill_fg)[#dr],
  )
}

#let social_url(net, user) = {
  let n = lower(net)
  if n == "linkedin" { return "https://linkedin.com/in/" + user }
  if n == "github" { return "https://github.com/" + user }
  if n == "x" or n == "twitter" { return "https://x.com/" + user }
  return user
}

#let social_display(net, user) = {
  let n = lower(net)
  if n == "linkedin" { return "linkedin.com/in/" + user }
  if n == "github" { return "github.com/" + user }
  if n == "x" or n == "twitter" { return "x.com/" + user }
  return user
}

// Lightweight inline Markdown renderer supporting **bold** and [label](url) (even combined)
#let render_bold(s) = {
  let bold_re = regex("\*\*([^*]+)\*\*")
  let bmatches = s.matches(bold_re)
  if bmatches.len() == 0 {
    return [#s]
  }
  let out = ()
  let cursor = 0
  for m in bmatches {
    if m.start > cursor { out.push(s.slice(cursor, m.start)) }
    out.push(strong(m.captures.at(0)))
    cursor = m.end
  }
  if cursor < s.len() { out.push(s.slice(cursor)) }
  return out.join()
}

#let md_inline(str_val) = {
  let s = str(str_val)
  let link_re = regex("\[([^\]]+)\]\(([^)]+)\)")
  let matches = s.matches(link_re)
  if matches.len() == 0 {
    return render_bold(s)
  }
  let out = ()
  let cursor = 0
  for m in matches {
    if m.start > cursor { out.push(render_bold(s.slice(cursor, m.start))) }
    out.push(link(m.captures.at(1), render_bold(m.captures.at(0))))
    cursor = m.end
  }
  if cursor < s.len() { out.push(render_bold(s.slice(cursor))) }
  return out.join()
}

#let title_case(key) = {
  let words = str(key).replace("_", " ").split(" ")
  words.map(w => upper(w.slice(0, 1)) + w.slice(1)).join(" ")
}

#let section_heading(title) = {
  v(1.05em)
  block(breakable: false, sticky: true, width: 100%, below: 0.6em)[
    #heading(level: 2, outlined: false)[#upper(title)]
    #line(length: 100%, stroke: 0.85pt + c_rule)
  ]
}

// Non-continuous vertical timeline item:
// - Connector line only appears on non-last items (terminates cleanly at the last dot)
// - White halo ring creates crisp visual breaks above and below every dot
// - Centered mathematically on the stroke center (x = 0)
#let timeline_indent = 1.15em
#let timeline_item(is_active: false, is_last: false, gap: 0.8em, body) = {
  let halo_r = 4.6pt
  let dot_r = 2.4pt
  block(
    width: 100%,
    inset: (
      left: timeline_indent,
      top: 0pt,
      bottom: if is_last { 0pt } else { gap },
    ),
    stroke: if is_last { none } else { (left: 1.2pt + c_rule) },
    below: 0pt,
  )[
    #place(
      left + top,
      dx: -timeline_indent - halo_r,
      dy: 0.14em - (halo_r - dot_r),
      box(width: halo_r * 2, height: halo_r * 2)[
        #align(center + horizon)[
          #circle(radius: halo_r, fill: c_bg)
        ]
        #place(center + horizon)[
          #circle(
            radius: dot_r,
            fill: if is_active { c_accent } else { c_muted },
          )
        ]
      ],
    )
    #body
  ]
}

// --- Header (strictly inside document body for ATS) ---
#let header_text = block(width: 100%)[
  #heading(level: 1, outlined: false)[#cv.name]
  #if "headline" in cv and cv.headline != none [
    #block(above: 0pt, below: 0.3em)[
      #text(size: 10.5pt, weight: "medium", fill: c_muted)[#cv.headline]
    ]
  ]
  #{
    let items = ()
    if "location" in cv and cv.location != none {
      items.push([#cv.location])
    }
    if "email" in cv and cv.email != none {
      items.push(link("mailto:" + cv.email, cv.email))
    }
    if "phone" in cv and cv.phone != none {
      items.push([#cv.phone])
    }
    if "website" in cv and cv.website != none {
      items.push(link(cv.website, cv.website))
    }
    if "social_networks" in cv and cv.social_networks != none {
      for sn in cv.social_networks {
        let u = social_url(sn.network, sn.username)
        let d = social_display(sn.network, sn.username)
        items.push(link(u, d))
      }
    }
    text(size: 9pt, fill: c_sub)[#items.join([  |  ])]
  }
]

#if photo_path != "" [
  #grid(
    columns: (auto, 1fr),
    column-gutter: 1.2em,
    align: horizon,
    box(
      width: 2.1cm,
      height: 2.1cm,
      radius: 50%,
      clip: true,
      stroke: 0.6pt + c_rule,
      image(photo_path, width: 100%, height: 100%, fit: "cover"),
    ),
    header_text,
  )
] else [
  #header_text
]

// Group consecutive experience entries sharing the same company,
// and consecutive education entries sharing the same institution.
#let group_entries(entries) = {
  let groups = ()
  for entry in entries {
    if type(entry) == dictionary and "company" in entry {
      if "roles" in entry {
        groups.push((kind: "company_group", company: entry.company, roles: entry.roles))
      } else if groups.len() > 0 and groups.last().kind == "company_group" and groups.last().company == entry.company {
        let prev = groups.pop()
        prev.roles.push(entry)
        groups.push(prev)
      } else {
        groups.push((kind: "company_group", company: entry.company, roles: (entry,)))
      }
    } else if type(entry) == dictionary and "institution" in entry {
      if "degrees" in entry {
        groups.push((kind: "edu_group", institution: entry.institution, degrees: entry.degrees))
      } else if groups.len() > 0 and groups.last().kind == "edu_group" and groups.last().institution == entry.institution {
        let prev = groups.pop()
        prev.degrees.push(entry)
        groups.push(prev)
      } else {
        groups.push((kind: "edu_group", institution: entry.institution, degrees: (entry,)))
      }
    } else {
      groups.push((kind: "other", entry: entry))
    }
  }
  return groups
}

#let render_edu_details(entry) = {
  if "highlights" in entry and entry.highlights != none and entry.highlights.len() > 0 {
    for h in entry.highlights [
      \ #text(size: 8.8pt, fill: c_muted)[#md_inline(h)]
    ]
  }
}

// --- Dynamic Section Renderer ---
#for (sec_key, entries) in cv.sections.pairs() [
  #section_heading(title_case(sec_key))

  #for item in group_entries(entries) {
    if item.kind == "company_group" and item.roles.len() > 1 {
      // Multi-role progression at the same company — kept together so timeline never splits across pages
      block(breakable: false, width: 100%, below: 0.9em)[
        #block(breakable: false, sticky: true, width: 100%, below: 0.45em)[
          #text(weight: "bold", size: 10.3pt, fill: c_dark)[#item.company]
        ]

        #pad(left: 0.45em)[
          #for (idx, role) in item.roles.enumerate() {
            let dr = fmt_range(role)
            let is_last = idx == item.roles.len() - 1
            timeline_item(is_active: is_present(role), is_last: is_last)[
              #block(breakable: false, sticky: true, width: 100%, below: 0.35em)[
                #text(weight: "bold", size: 9.7pt, fill: c_sub)[#role.position]
                #h(1fr)
                #date_badge(dr)
              ]
              #if "summary" in role and role.summary != none {
                par[#md_inline(role.summary)]
              }
              #if "highlights" in role and role.highlights != none {
                list(
                  indent: 0.45em,
                  body-indent: 0.45em,
                  spacing: 0.68em,
                  tight: false,
                  marker: [•],
                  ..role.highlights.map(h => md_inline(h)),
                )
              }
            ]
          }
        ]
      ]
    } else if item.kind == "company_group" {
      // Single-role ExperienceEntry
      let entry = item.roles.first()
      let dr = fmt_range(entry)
      block(breakable: false, sticky: true, width: 100%, below: 0.35em)[
        #text(weight: "bold", size: 10.3pt, fill: c_dark)[#entry.company] \
        #v(0.12em)
        #text(weight: "bold", size: 9.7pt, fill: c_sub)[#entry.position]
        #h(1fr)
        #date_badge(dr)
      ]
      if "summary" in entry and entry.summary != none {
        par[#md_inline(entry.summary)]
      }
      if "highlights" in entry and entry.highlights != none {
        list(
          indent: 0.6em,
          body-indent: 0.45em,
          spacing: 0.68em,
          tight: false,
          marker: [•],
          ..entry.highlights.map(h => md_inline(h)),
        )
      }
      v(0.75em)
    } else if item.kind == "edu_group" and item.degrees.len() > 1 {
      // Multi-degree progression at the same institution
      block(breakable: false, sticky: true, width: 100%, below: 0.55em)[
        #text(weight: "bold", size: 10.3pt, fill: c_dark)[#item.institution]
      ]

      pad(left: 0.45em, bottom: 1.0em)[
        #for (idx, deg) in item.degrees.enumerate() {
          let dr = fmt_range(deg)
          let is_last = idx == item.degrees.len() - 1
          let degree_line = if "degree" in deg and deg.degree != none {
            deg.degree + " in " + deg.area
          } else {
            deg.area
          }
          timeline_item(is_active: is_present(deg), is_last: is_last, gap: 1.15em)[
            #block(breakable: false, width: 100%, below: 0pt)[
              #text(weight: "bold", size: 9.7pt, fill: c_sub)[#degree_line]
              #h(1fr)
              #date_badge(dr)#render_edu_details(deg)
            ]
          ]
        }
      ]
    } else if item.kind == "edu_group" {
      // Single-degree EducationEntry
      let entry = item.degrees.first()
      let dr = fmt_range(entry)
      let degree_line = if "degree" in entry and entry.degree != none {
        entry.degree + " in " + entry.area
      } else {
        entry.area
      }
      block(breakable: false, width: 100%, below: 0.9em)[
        #text(weight: "bold", size: 10.3pt, fill: c_dark)[#entry.institution] \
        #v(0.22em)
        #text(weight: "bold", size: 9.7pt, fill: c_sub)[#degree_line]
        #h(1fr)
        #date_badge(dr)#render_edu_details(entry)
      ]
    } else {
      let entry = item.entry
      if type(entry) == str {
        par[#md_inline(entry)]
      } else if "label" in entry and "details" in entry {
        // Strictly single-column inline paragraph so spatial extractors (e.g. pdfminer)
        // never cluster labels away from their skill values across section boundaries.
        block(breakable: false, width: 100%, below: 0.5em)[
          #text(weight: "bold", size: 9.1pt, fill: c_dark)[#entry.label:] #text(size: 9.1pt, fill: c_ink)[#md_inline(entry.details)]
        ]
      } else if "name" in entry {
        let dr = fmt_range(entry)
        let has_highlights = "highlights" in entry and entry.highlights != none and entry.highlights.len() > 0
        block(breakable: false, sticky: has_highlights, width: 100%, below: if has_highlights { 0.38em } else { 0.55em })[
          #text(weight: "bold", size: 9.8pt, fill: c_dark)[#md_inline(entry.name)]
          #h(1fr)
          #date_badge(dr)
          #if "summary" in entry and entry.summary != none [ \ #md_inline(entry.summary) ]
        ]
        if has_highlights {
          list(
            indent: 0.6em,
            body-indent: 0.45em,
            spacing: 0.68em,
            tight: false,
            marker: [•],
            ..entry.highlights.map(h => md_inline(h)),
          )
          v(0.55em)
        }
      } else if "bullet" in entry {
        list(indent: 0.7em, body-indent: 0.45em, marker: [•], md_inline(entry.bullet))
      }
    }
  }
]
