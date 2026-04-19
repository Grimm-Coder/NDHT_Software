# NDHT Automated Hardness Testing System

## Overview
The NDHT Automated Hardness Testing System is designed to measure the hardness of various materials automatically. This system can be integrated into manufacturing lines for real-time quality assurance, ensuring that products meet specified hardness requirements.

## Architecture
The architecture of the NDHT system consists of:
- **User Interface**: A dashboard for monitoring tests and results.
- **Control Unit**: Manages the testing process and records results.
- **Measurement Module**: Includes sensors to measure hardness.
- **Data Storage**: Stores test results for analysis and record-keeping.

## Prerequisites
Before installing the NDHT system, ensure you have the following:
- Operating System: Windows 10 or higher / Linux (Ubuntu 18.04 or higher)
- Java Runtime Environment (JRE) 8 or higher
- Database software (MySQL, PostgreSQL)
- Required libraries and dependencies (see Installation section)

## Installation
To install the NDHT system:
1. Clone the repository.
   ```bash
   git clone https://github.com/Grimm-Coder/NDHT_Software.git
   cd NDHT_Software
   ```
2. Install required libraries:
   ```bash
   pip install -r requirements.txt
   ```
3. Configure the database connection in the `config.json` file.
4. Run the installation script:
   ```bash
   ./install.sh
   ```

## Usage
To use the NDHT system:
1. Start the control unit by running:
   ```bash
   java -jar NDHTControlUnit.jar
   ```
2. Monitor the user interface to initiate tests and view results in real-time.

## Configuration
Configuration settings are stored in `config.json`. You can adjust:
- Database credentials
- Measurement parameters
- User settings

## Output Files
The system generates the following output files:
- Test results in CSV format.
- Logs for each test run, detailing parameters and outcomes.

## Troubleshooting
- **Common Issues**:
  - If the application fails to start, check that you have the correct JRE version.
  - Database connection errors may indicate incorrect credentials in `config.json`.

For further assistance, consult the documentation or reach out to the support team.

## Hardware Integration
The NDHT system can be integrated with various hardware components, including:
- Hardness testing machines (ensure compatibility).
- Additional sensors for enhanced measurements.
- Communication modules for interfacing with other systems.

Ensure that hardware components are properly configured before running tests.