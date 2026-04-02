window.HOMEAIHUB_TV_DESIGN_MODE = true;
window.HOMEAIHUB_TV_DESIGN_DATA = {
  scenes: {
    morning: {
      mode: "dashboard",
      scene_label: "Morning Briefing",
      scene_hint: "School run, clinic prep, and family notes",
      dashboard_mode: "always_on",
      generated_at: "2026-04-01T07:12:00",
      header: {
        time: "07:12",
        date: "April 1",
        weekday: "Wednesday",
        weather: "18C 12 / 21",
        status: "ONLINE",
        tv_power: "on",
        tv_input: "dashboard"
      },
      hero_alert: {
        title: "Morning briefing ready",
        message: "Three family schedules, one school item, and one medication reminder need attention.",
        priority: "high"
      },
      wake_overlay: {
        title: "Lumi is listening",
        message: "Hey master, Need any help",
        agent: "voice-automation-agent",
        time: "07:12:18"
      },
      focus: {
        title: "Morning Focus",
        summary: "Today is school and clinic day. Alex needs the field-trip form signed before leaving.",
        pending_confirmations: 2,
        next_up: {
          title: "School drop-off",
          time: "08:00 AM"
        }
      },
      system_tiles: [
        { label: "Home Mode", value: "family-hub", tone: "green" },
        { label: "Dashboard", value: "always_on", tone: "blue" },
        { label: "Voice", value: "active", tone: "orange" },
        { label: "Agent", value: "lumi-core", tone: "pink" }
      ],
      today_schedule: [
        {
          title: "School Drop-off",
          person: "Mom",
          location: "Hillside School",
          summary: "Bring field-trip form",
          priority: "high",
          time: "08:00 AM",
          color: "pink",
          avatar_url: "/dashboard-static/assets/avatars/mom.svg"
        },
        {
          title: "Design Review",
          person: "Dad",
          location: "Downtown Office",
          summary: "Slides final pass",
          priority: "normal",
          time: "09:30 AM",
          color: "blue",
          avatar_url: "/dashboard-static/assets/avatars/dad.svg"
        },
        {
          title: "Math Club",
          person: "Alex",
          location: "School Hall",
          summary: "Uniform day",
          priority: "normal",
          time: "03:45 PM",
          color: "orange",
          avatar_url: "/dashboard-static/assets/avatars/alex.svg"
        },
        {
          title: "Piano Practice",
          person: "Emma",
          location: "Living Room",
          summary: "Warm up 20 minutes",
          priority: "low",
          time: "06:30 PM",
          color: "green",
          avatar_url: "/dashboard-static/assets/avatars/emma.svg"
        }
      ],
      timeline: [
        {
          person: "Mom",
          color: "pink",
          avatar_url: "/dashboard-static/assets/avatars/mom.svg",
          events: [
            { title: "Drop-off", time: "08:00 AM", color: "pink" },
            { title: "Clinic", time: "11:00 AM", color: "pink" }
          ]
        },
        {
          person: "Dad",
          color: "blue",
          avatar_url: "/dashboard-static/assets/avatars/dad.svg",
          events: [
            { title: "Review", time: "09:30 AM", color: "blue" },
            { title: "Client Call", time: "02:00 PM", color: "blue" }
          ]
        },
        {
          person: "Alex",
          color: "orange",
          avatar_url: "/dashboard-static/assets/avatars/alex.svg",
          events: [
            { title: "Math Club", time: "03:45 PM", color: "orange" },
            { title: "Homework", time: "06:15 PM", color: "orange" }
          ]
        },
        {
          person: "Emma",
          color: "green",
          avatar_url: "/dashboard-static/assets/avatars/emma.svg",
          events: [
            { title: "Piano", time: "06:30 PM", color: "green" },
            { title: "Reading", time: "08:00 PM", color: "green" }
          ]
        }
      ],
      reminders: [
        { title: "Sign field-trip form", person: "Alex", time: "Before 8:00", summary: "Put the signed form into the blue backpack.", priority: "high" },
        { title: "Take medicine", person: "Mom", time: "After breakfast", summary: "One tablet with water.", priority: "normal" },
        { title: "Pack presentation remote", person: "Dad", time: "Before 9:00", summary: "Desk drawer, second shelf.", priority: "low" }
      ],
      infos: [
        { title: "Driveway snapshot sorted", person: "HomeAIHub", time: "06:58", summary: "Three vehicle images placed in Morning Security.", priority: "low" },
        { title: "Voice memo summarized", person: "HomeAIHub", time: "06:46", summary: "Grandma's shopping note saved into Family Notes.", priority: "normal" },
        { title: "Weather update", person: "HomeAIHub", time: "06:30", summary: "Rain may start after 8 PM.", priority: "low" }
      ],
      notifications: [
        { id: 101, title: "Leave by 7:45", message: "Traffic is heavier today. Suggested earlier departure for school.", person: "Mom", location: "School Route", priority: "high" },
        { id: 102, title: "Field-trip form pending", message: "A photo note was recognized and needs guardian confirmation.", person: "Alex", location: "Kitchen counter", priority: "normal" }
      ],
      footer: {
        voice_status: "Good morning. Your family briefing is ready.",
        summary: "3 reminders and 2 confirmations pending",
        recent_update: "Morning schedule synced from photos and notes",
        active_agent: "voice-automation-agent",
        last_route: "voice.wake_ack"
      }
    },
    away: {
      mode: "dashboard",
      scene_label: "Leave Home",
      scene_hint: "Traffic, packing, and departure checks",
      dashboard_mode: "focus",
      generated_at: "2026-04-01T08:42:00",
      header: {
        time: "08:42",
        date: "April 1",
        weekday: "Wednesday",
        weather: "19C 13 / 22",
        status: "ONLINE",
        tv_power: "on",
        tv_input: "dashboard"
      },
      hero_alert: {
        title: "Leave-home reminder",
        message: "Dad should leave in 15 minutes for the dentist appointment. Umbrella recommended.",
        priority: "high"
      },
      wake_overlay: {
        title: "Lumi is listening",
        message: "Transport and weather checks are ready",
        agent: "home-orchestrator-agent",
        time: "08:42:06"
      },
      focus: {
        title: "Departure Window",
        summary: "Traffic is moderate. Packing, medicine, and front-door checklist are still active.",
        pending_confirmations: 1,
        next_up: {
          title: "Dentist arrival",
          time: "11:00 AM"
        }
      },
      system_tiles: [
        { label: "Home Mode", value: "departure", tone: "orange" },
        { label: "Doors", value: "locked", tone: "green" },
        { label: "Voice", value: "active", tone: "orange" },
        { label: "Agent", value: "route-check", tone: "pink" }
      ],
      today_schedule: [
        {
          title: "Doctor Appointment",
          person: "Mom",
          location: "City Dental",
          summary: "Bring insurance card",
          priority: "high",
          time: "11:00 AM",
          color: "pink",
          avatar_url: "/dashboard-static/assets/avatars/mom.svg"
        },
        {
          title: "Product Sync",
          person: "Dad",
          location: "Office B",
          summary: "Laptop and samples",
          priority: "normal",
          time: "01:30 PM",
          color: "blue",
          avatar_url: "/dashboard-static/assets/avatars/dad.svg"
        },
        {
          title: "Tutoring class",
          person: "Alex",
          location: "Learning Studio",
          summary: "Bring geometry notebook",
          priority: "normal",
          time: "04:30 PM",
          color: "orange",
          avatar_url: "/dashboard-static/assets/avatars/alex.svg"
        },
        {
          title: "Dinner Gathering",
          person: "Emma",
          location: "Grandma's House",
          summary: "Family dinner",
          priority: "high",
          time: "07:00 PM",
          color: "green",
          avatar_url: "/dashboard-static/assets/avatars/emma.svg"
        }
      ],
      timeline: [
        {
          person: "Mom",
          color: "pink",
          avatar_url: "/dashboard-static/assets/avatars/mom.svg",
          events: [
            { title: "Doctor", time: "11:00 AM", color: "pink" },
            { title: "Pickup", time: "05:10 PM", color: "pink" }
          ]
        },
        {
          person: "Dad",
          color: "blue",
          avatar_url: "/dashboard-static/assets/avatars/dad.svg",
          events: [
            { title: "Sync", time: "01:30 PM", color: "blue" },
            { title: "Gym", time: "08:00 PM", color: "blue" }
          ]
        },
        {
          person: "Alex",
          color: "orange",
          avatar_url: "/dashboard-static/assets/avatars/alex.svg",
          events: [
            { title: "Tutoring", time: "04:30 PM", color: "orange" },
            { title: "Homework", time: "06:15 PM", color: "orange" }
          ]
        },
        {
          person: "Emma",
          color: "green",
          avatar_url: "/dashboard-static/assets/avatars/emma.svg",
          events: [
            { title: "Dinner", time: "07:00 PM", color: "green" }
          ]
        }
      ],
      reminders: [
        { title: "Umbrella by the door", person: "Family", time: "Before leaving", summary: "Rain risk after lunch.", priority: "normal" },
        { title: "Insurance card", person: "Mom", time: "Before 10:00", summary: "Inside beige handbag.", priority: "high" },
        { title: "Package pickup", person: "Dad", time: "Anytime", summary: "Garage shelf before 8 PM.", priority: "low" }
      ],
      infos: [
        { title: "Front-door camera note", person: "HomeAIHub", time: "08:33", summary: "Package carrier ring detected and summarized.", priority: "normal" },
        { title: "Traffic check complete", person: "HomeAIHub", time: "08:30", summary: "Travel time to City Dental increased by 8 minutes.", priority: "low" },
        { title: "Weather update", person: "HomeAIHub", time: "08:20", summary: "Light showers possible this afternoon.", priority: "low" }
      ],
      notifications: [
        { id: 201, title: "Leave-home reminder", message: "Dad should leave in 15 minutes.", person: "Dad", location: "City Dental", priority: "high" }
      ],
      footer: {
        voice_status: "Departure checklist is ready.",
        summary: "2 transport reminders active",
        recent_update: "Traffic and weather were refreshed",
        active_agent: "home-orchestrator-agent",
        last_route: "announce.play"
      }
    },
    evening: {
      mode: "dashboard",
      scene_label: "Evening Summary",
      scene_hint: "Albums, homework, and wrap-up reminders",
      dashboard_mode: "always_on",
      generated_at: "2026-04-01T19:50:00",
      header: {
        time: "19:50",
        date: "April 1",
        weekday: "Wednesday",
        weather: "16C 12 / 21",
        status: "ONLINE",
        tv_power: "on",
        tv_input: "dashboard"
      },
      hero_alert: {
        title: "Evening wrap-up",
        message: "Photo album, homework summary, and one medication reminder are ready for review.",
        priority: "normal"
      },
      wake_overlay: {
        title: "Lumi is listening",
        message: "Would you like the evening recap",
        agent: "family-intake-agent",
        time: "19:50:42"
      },
      focus: {
        title: "Evening Focus",
        summary: "Homework was recognized from desk photos, dinner photos were grouped, and one reminder remains.",
        pending_confirmations: 1,
        next_up: {
          title: "Bedtime routine",
          time: "09:00 PM"
        }
      },
      system_tiles: [
        { label: "Home Mode", value: "evening", tone: "blue" },
        { label: "Photos", value: "12 sorted", tone: "green" },
        { label: "Voice", value: "standby", tone: "orange" },
        { label: "Agent", value: "album-summarizer", tone: "pink" }
      ],
      today_schedule: [
        {
          title: "Dinner Gathering",
          person: "Family",
          location: "Grandma's House",
          summary: "Photos and notes captured",
          priority: "normal",
          time: "07:00 PM",
          color: "green",
          avatar_url: "/dashboard-static/assets/avatars/emma.svg"
        },
        {
          title: "Homework Review",
          person: "Alex",
          location: "Study Room",
          summary: "Math pages detected from photo",
          priority: "normal",
          time: "08:10 PM",
          color: "orange",
          avatar_url: "/dashboard-static/assets/avatars/alex.svg"
        },
        {
          title: "Medication Reminder",
          person: "Mom",
          location: "Kitchen",
          summary: "Take after dinner",
          priority: "high",
          time: "08:30 PM",
          color: "pink",
          avatar_url: "/dashboard-static/assets/avatars/mom.svg"
        },
        {
          title: "Quiet Reading",
          person: "Emma",
          location: "Bedroom",
          summary: "20 minute wind-down",
          priority: "low",
          time: "08:45 PM",
          color: "green",
          avatar_url: "/dashboard-static/assets/avatars/emma.svg"
        }
      ],
      timeline: [
        {
          person: "Mom",
          color: "pink",
          avatar_url: "/dashboard-static/assets/avatars/mom.svg",
          events: [
            { title: "Medicine", time: "08:30 PM", color: "pink" }
          ]
        },
        {
          person: "Dad",
          color: "blue",
          avatar_url: "/dashboard-static/assets/avatars/dad.svg",
          events: [
            { title: "Photo Review", time: "08:20 PM", color: "blue" },
            { title: "Mail Reply", time: "09:10 PM", color: "blue" }
          ]
        },
        {
          person: "Alex",
          color: "orange",
          avatar_url: "/dashboard-static/assets/avatars/alex.svg",
          events: [
            { title: "Homework", time: "08:10 PM", color: "orange" },
            { title: "Shower", time: "08:55 PM", color: "orange" }
          ]
        },
        {
          person: "Emma",
          color: "green",
          avatar_url: "/dashboard-static/assets/avatars/emma.svg",
          events: [
            { title: "Reading", time: "08:45 PM", color: "green" }
          ]
        }
      ],
      reminders: [
        { title: "Review dinner photos", person: "Family", time: "Tonight", summary: "12 images auto-grouped under Grandma Dinner.", priority: "low" },
        { title: "Take medicine", person: "Mom", time: "08:30 PM", summary: "After food.", priority: "high" },
        { title: "Sign spelling sheet", person: "Alex", time: "Before bedtime", summary: "Notebook left on desk.", priority: "normal" }
      ],
      infos: [
        { title: "Family album updated", person: "HomeAIHub", time: "19:42", summary: "Dinner photos grouped and tagged.", priority: "low" },
        { title: "Homework note summarized", person: "HomeAIHub", time: "19:28", summary: "Math pages and teacher notes saved.", priority: "normal" },
        { title: "Voice clip archived", person: "Grandma", time: "19:11", summary: "Recipe voice memo transcribed.", priority: "low" }
      ],
      notifications: [
        { id: 301, title: "Medication reminder", message: "Medicine should be taken after dinner.", person: "Mom", location: "Kitchen", priority: "high" }
      ],
      footer: {
        voice_status: "Evening recap is available.",
        summary: "1 high-priority reminder left tonight",
        recent_update: "Photo album and homework notes were summarized",
        active_agent: "family-intake-agent",
        last_route: "intake.photo"
      }
    },
    emergency: {
      mode: "dashboard",
      scene_label: "Emergency Alert",
      scene_hint: "Doorbell, camera, and confirmation flow",
      dashboard_mode: "wake_overlay",
      generated_at: "2026-04-01T21:08:00",
      header: {
        time: "21:08",
        date: "April 1",
        weekday: "Wednesday",
        weather: "15C 12 / 21",
        status: "ALERT",
        tv_power: "on",
        tv_input: "dashboard"
      },
      hero_alert: {
        title: "Emergency door event",
        message: "Front-door motion and repeated bell detected. Waiting for voice confirmation.",
        priority: "high"
      },
      wake_overlay: {
        title: "Lumi needs confirmation",
        message: "I detected repeated doorbell activity. Should I announce through the speaker",
        agent: "home-orchestrator-agent",
        time: "21:08:11"
      },
      focus: {
        title: "Urgent Review",
        summary: "Camera snapshots were grouped and a voice announcement is waiting for approval.",
        pending_confirmations: 1,
        next_up: {
          title: "Confirm emergency response",
          time: "Now"
        }
      },
      system_tiles: [
        { label: "Home Mode", value: "alert", tone: "orange" },
        { label: "Sensors", value: "door event", tone: "pink" },
        { label: "Voice", value: "armed", tone: "orange" },
        { label: "Agent", value: "safety-check", tone: "pink" }
      ],
      today_schedule: [
        {
          title: "Front Door Motion",
          person: "HomeAIHub",
          location: "Front Door",
          summary: "Three motion events in 30 seconds",
          priority: "high",
          time: "09:07 PM",
          color: "orange",
          avatar_url: "/dashboard-static/assets/avatars/dad.svg"
        },
        {
          title: "Doorbell Ring",
          person: "HomeAIHub",
          location: "Front Door",
          summary: "Two rings detected from audio",
          priority: "high",
          time: "09:08 PM",
          color: "pink",
          avatar_url: "/dashboard-static/assets/avatars/mom.svg"
        },
        {
          title: "Camera Snapshot",
          person: "HomeAIHub",
          location: "Security Feed",
          summary: "Visitor holding parcel",
          priority: "normal",
          time: "09:08 PM",
          color: "blue",
          avatar_url: "/dashboard-static/assets/avatars/alex.svg"
        },
        {
          title: "Await Voice Confirmation",
          person: "Family",
          location: "Living Room TV",
          summary: "Say confirm visitor or ignore",
          priority: "high",
          time: "Now",
          color: "green",
          avatar_url: "/dashboard-static/assets/avatars/emma.svg"
        }
      ],
      timeline: [
        {
          person: "Security",
          color: "orange",
          avatar_url: "/dashboard-static/assets/avatars/dad.svg",
          events: [
            { title: "Motion", time: "09:07 PM", color: "orange" },
            { title: "Doorbell", time: "09:08 PM", color: "pink" }
          ]
        },
        {
          person: "Cameras",
          color: "blue",
          avatar_url: "/dashboard-static/assets/avatars/alex.svg",
          events: [
            { title: "Snapshot", time: "09:08 PM", color: "blue" },
            { title: "OCR check", time: "09:08 PM", color: "blue" }
          ]
        },
        {
          person: "Voice",
          color: "green",
          avatar_url: "/dashboard-static/assets/avatars/emma.svg",
          events: [
            { title: "Await confirm", time: "Now", color: "green" }
          ]
        }
      ],
      reminders: [
        { title: "Confirm visitor", person: "Family", time: "Now", summary: "Speak confirm visitor to play response.", priority: "high" },
        { title: "Check package note", person: "HomeAIHub", time: "Next", summary: "OCR found a possible courier label.", priority: "normal" },
        { title: "Review camera clip", person: "Dad", time: "Tonight", summary: "Saved in Front Door Events.", priority: "low" }
      ],
      infos: [
        { title: "Visitor looks familiar", person: "HomeAIHub", time: "21:08", summary: "Face similarity suggests regular courier.", priority: "normal" },
        { title: "Screenshot archived", person: "HomeAIHub", time: "21:08", summary: "Three snapshots saved in Security Inbox.", priority: "low" },
        { title: "Speaker action paused", person: "HomeAIHub", time: "21:08", summary: "Waiting for household confirmation.", priority: "low" }
      ],
      notifications: [
        { id: 401, title: "Front-door event", message: "Repeated bell detected. Confirm visitor response.", person: "HomeAIHub", location: "Front Door", priority: "high" }
      ],
      footer: {
        voice_status: "Emergency review is waiting for confirmation.",
        summary: "1 urgent confirmation required",
        recent_update: "Camera and audio were grouped into one incident",
        active_agent: "home-orchestrator-agent",
        last_route: "safety.confirmation"
      }
    },
    pairing: {
      mode: "pairing",
      scene_label: "Pairing",
      scene_hint: "TV onboarding before remote devices are linked",
      device: { device_name: "HomeAIHub Family Box" },
      pairing: {
        device_id: "hub-design-001",
        claim_token: "A8K4-P2Q9",
        claim_expires_at: "2026-04-01 23:59",
        claim_url: "https://pair.homeaihub.app/claim/hub-design-001",
        qr_payload: {
          type: "homeaihub-claim",
          device_id: "hub-design-001",
          claim_token: "A8K4-P2Q9",
          gateway: "https://homeaihub.app",
          claim_endpoint: "https://homeaihub.app/api/gateway/device/claim"
        }
      },
      onboarding: {
        title: "HomeAIHub pairing ready",
        subtitle: "Scan once from the family app to connect this TV box and unlock remote controls.",
        steps: [
          "Open the HomeAIHub app on your phone or tablet.",
          "Scan the pairing card shown on this TV.",
          "Confirm the owner and family binding.",
          "After pairing, all remote messages, photos, and voice clips route here."
        ]
      }
    }
  },
  rotation: ["morning", "away", "evening", "emergency", "pairing"]
};
