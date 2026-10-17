# 🧪 Smart Urinalysis
### A Python-Based Desktop Application for Urine Test Analysis and Health Monitoring

Smart Urinalysis is a healthcare-focused desktop application designed to organize patient information, record urine test-strip results, highlight abnormal readings, visualize test trends, and generate PDF reports.

The project provides a structured digital workflow for managing urinalysis records through a graphical interface. By combining patient record management, parameter-based test entry, result flagging, and reporting, it demonstrates how software can support the organization and review of urine test information.

> **Project type:** Healthcare Technology | Desktop Application | Python Mini-Project

## 📌 Table of Contents

- [About the Project](#-about-the-project)
- [Problem Statement](#-problem-statement)
- [Objectives](#-objectives)
- [Features](#-features)
- [How It Works](#-how-it-works)
- [Technology Stack](#️-technology-stack)
- [Project Structure](#-project-structure)
- [Installation and Setup](#-installation-and-setup)
- [Team and Contributions](#-team-and-contributions)
- [Future Scope](#-future-scope)
- [Disclaimer](#️-medical-disclaimer)

## 🔍 About the Project

Urinalysis is a commonly used laboratory procedure for examining urine characteristics that can provide information relevant to health assessment. However, manually maintaining patient records, documenting test results, identifying abnormal values, and comparing previous tests can be time-consuming.

Smart Urinalysis addresses the record-management and result-review aspects of this workflow through a desktop application built with Python and Tkinter, with SQLite used for data storage.

The application supports the recording of ten urine-test parameters, abnormal-result flags, historical trend charts, and PDF report generation.

The project was developed by a team of **four members who contributed equally**. While the repository is hosted under one member's GitHub account, the project credit is shared equally among all four team members.

## 🎯 Problem Statement

Manual management of urinalysis records can make it difficult to maintain organized patient histories, review multiple test parameters, identify readings that may need attention, and prepare reports efficiently.

The objective of Smart Urinalysis is to provide a simple desktop-based system that brings these activities together in one place, helping users manage and review recorded urine test information more systematically.

## 🎯 Objectives

- Develop a graphical desktop application for urinalysis record management.
- Maintain patient information in a structured database.
- Enable entry and review of ten urine-test parameters.
- Highlight readings identified as abnormal according to the application's configured rules.
- Visualize historical test results through trend charts.
- Generate downloadable or printable PDF reports.
- Apply Python programming, database management, data visualization, and report-generation concepts to a healthcare use case.

## ✨ Features

### 👤 1. Patient Record Management
Maintain patient records and associate urinalysis results with the relevant patient.

### 🧪 2. Ten-Parameter Test Entry
Record results for the ten urine-test parameters supported by the application, enabling structured documentation of test readings.

### 🚩 3. Abnormal-Result Flags
Highlight readings that meet the application's configured abnormal-result criteria, making results requiring further review easier to identify.

### 📈 4. Historical Trend Charts
Visualize recorded test results over time to help users compare previous readings and observe changes in the available data.

### 📄 5. PDF Report Generation
Generate PDF reports of recorded urinalysis information for documentation and review.

### 🖥️ 6. Desktop Graphical Interface
Use a graphical user interface built with Tkinter to interact with patient records and test information without relying entirely on terminal commands.

### 🗄️ 7. Local Database Storage
Use SQLite to store application data in a local database, supporting structured record management between application sessions.

## ⚙️ How It Works

<CodeBlock language="mermaid">flowchart TD
    A["Launch Smart Urinalysis"] --> B["Open Desktop Interface"]
    B --> C["Select or Manage Patient Record"]
    C --> D["Enter Urine Test Parameters"]
    D --> E["Save Test Information"]
    E --> F["Review Configured Abnormal Flags"]
    F --> G["View Historical Trend Charts"]
    G --> H["Generate PDF Report"]
    E <--> I[("SQLite Database")]
</CodeBlock>

The application brings together patient information and test results in a single desktop workflow. Recorded data can be reviewed, relevant flags can be inspected, historical trends can be visualized, and PDF reports can be generated.

## 🛠️ Technology Stack

| Technology | Purpose |
|---|---|
| Python | Core application logic |
| Tkinter | Desktop graphical user interface |
| SQLite | Local database storage |
| Matplotlib | Data visualization and trend charts |
| ReportLab | PDF report generation |
| Git and GitHub | Version control and collaborative development |

## 📁 Project Structure

The repository contains a `urinalysis_dashboard` directory alongside the root README. The application files are organized under that project directory.

```text
smart_urinalaysis/
├── urinalysis_dashboard/
│   └── Application source files
└── README.md
```

The precise internal file names and module structure should be documented from the current source files.

## 🚀 Installation and Setup

### Prerequisites

- Python 3 installed on your system
- Git
- pip, Python's package installer

### 1. Clone the Repository

```bash
git clone https://github.com/zaaz-png/smart_urinalaysis.git
cd smart_urinalaysis
```

### 2. Open the Application Directory

```bash
cd urinalysis_dashboard
```

### 3. Install Dependencies

Install the packages required by the project. If a `requirements.txt` file is available, run:

```bash
python3 -m pip install -r requirements.txt
```

If no dependency file exists, install the required packages listed in the source code, including Matplotlib and ReportLab where applicable.

### 4. Run the Application

Run the main Python application file from the project directory:

```bash
python3 <main_file>.py
```

Replace `<main_file>.py` with the actual entry-point filename in the repository.

**Note:** The precise startup command depends on the current source-file names and dependency configuration.

## 👥 Team and Contributions

Smart Urinalysis was developed collaboratively by a team of four members. **All four members contributed equally to the project**, and each deserves equal recognition for the collective work.

| Team Member | GitHub Profile | Contribution |
|---|---|---|
| Member 1 | [GitHub Profile](https://github.com/username1) | Equal project contribution |
| Member 2 | [GitHub Profile](https://github.com/username2) | Equal project contribution |
| Member 3 | [GitHub Profile](https://github.com/username3) | Equal project contribution |
| Member 4 | [GitHub Profile](https://github.com/username4) | Equal project contribution |

### 🤝 Collaboration Statement

The project was planned, developed, and refined through the collaborative efforts of all four team members. All members are equally credited for their contributions to the project's overall development and implementation.

The GitHub repository owner manages the hosting of the project, while repository ownership does not indicate a greater share of the team's contributions.

## 🔮 Future Scope

Potential future enhancements include:

- Adding patient search, filtering, and improved record navigation.
- Improving comparison of multiple historical test reports.
- Introducing configurable reference ranges and clearer explanations of flagged readings.
- Enhancing report formatting with additional charts and patient details.
- Adding secure backup and export options for records.
- Exploring integration with laboratory equipment or validated digital test-strip readers.

These are proposed enhancements and should not be interpreted as features already implemented.

## ⚠️ Medical Disclaimer

Smart Urinalysis is an educational software project for organizing and reviewing recorded urine-test information. It is not a certified medical diagnostic device.

Abnormal-result flags and visualized readings must not be interpreted as a definitive diagnosis. The application does not replace laboratory testing, clinical evaluation, or advice from a qualified healthcare professional.

## 📚 Learning Outcomes

This project demonstrates practical application of:

- Python desktop application development
- GUI design using Tkinter
- Database integration with SQLite
- Data visualization using Matplotlib
- PDF document generation using ReportLab
- Collaborative software development using Git and GitHub

## 📄 License

Check the repository for a license file and its applicable terms. If no license has been added, the project's reuse and distribution permissions should be clarified before selecting one.

---

**Smart Urinalysis — Built collaboratively by four team members, with equal contributions.**
