# Bug Report for "Pretty Good AI" Transcripts

## Issue 1: Incomplete Responses
### Scenario: scheduling_new
- **What the agent said or failed to do**: The agent failed to articulate clearly and provided incomplete responses multiple times, leading to significant confusion. For example, there were points where it just cut off mid-sentence: "to schedule your..." 
- **Expected behavior**: The agent should provide complete statements and clear instructions to the user to avoid confusion.
- **Severity**: High

---

## Issue 2: Incorrect Date of Birth Default
### Scenario: various (e.g., scheduling_new, refill_simple)
- **What the agent said or failed to do**: The agent consistently set the default date of birth to "July fourth two thousand," which is irrelevant to the patient's actual date of birth.
- **Expected behavior**: The agent should either ask for the patient's date of birth after initial input or not assign a default date unless necessary. 
- **Severity**: High

---

## Issue 3: Repetition of Questions
### Scenario: scheduling_returning
- **What the agent said or failed to do**: The agent repeatedly asked for the patient's first and last name, even after the patient had already provided that information.
- **Expected behavior**: The agent should recognize previously provided information, avoiding unnecessary redundancy and frustration for the patient.
- **Severity**: High

---

## Issue 4: Incorrect Handling of Patient Profiles
### Scenario: scheduling/rescheduling various
- **What the agent said or failed to do**: The agent insisted on creating a demo patient profile before proceeding with a common request, which confused and frustrated the patient. There was a failure to recognize existing profiles.
- **Expected behavior**: It should either recognize existing profiles or allow the patient to directly state their name and address their inquiries without insisting on a demo profile creation.
- **Severity**: Medium

---

## Issue 5: Failure to Provide Requested Information
### Scenario: location_directions/office_hours
- **What the agent said or failed to do**: The agent failed to provide specific details regarding office hours and directions and defaulted to generic advice without checking.
- **Expected behavior**: It should have either offered available information related to hours or directions or provided a means for the patient to receive that information directly.
- **Severity**: Critical

---

## Issue 6: Unclear Responses
### Scenario: refill_simple
- **What the agent said or failed to do**: The agent's responses often lacked clarity, such as using jargon that was difficult for patients to understand, leading to "I don’t know" or unclear answers.
- **Expected behavior**: The agent should communicate clearly and simply, avoiding jargon and ensuring patients understand all instructions or options provided.
- **Severity**: High

---

## Issue 7: Inconsistent Transfer Handling
### Scenario: various, including insurance queries
- **What the agent said or failed to do**: The agent inconsistently either transferred the patient to the appropriate team or provided incorrect statements about not being able to access information.
- **Expected behavior**: The agent should consistently transfer to the appropriate support team for questions outside its scope or provide accurate information more reliably.
- **Severity**: Medium

---

## Issue 8: Connectivity Issues
### Scenario: various transfer requests
- **What the agent said or failed to do**: There were multiple instances where patients were incorrectly connected to a test line instead of the appropriate support or agents, which left them confused.
- **Expected behavior**: Ensure that patients are transferred correctly to the relevant departments and verify connections to avoid confusion.
- **Severity**: Critical

---

## Issue 9: Lack of Empathy or Supportive Language
### Scenario: emotional_anxious 
- **What the agent said or failed to do**: The AI did not display empathy towards anxious patients seeking sensitive information such as lab results.
- **Expected behavior**: The agent should use supportive language and acknowledge the patient's feelings to improve user experience and comfort.
- **Severity**: Medium

---

## Issue 10: Communication during Language Barrier
### Scenario: non_english_speaker
- **What the agent said or failed to do**: The AI did not effectively handle the language barrier and offered minimal supportive structures for non-English speaking patients.
- **Expected behavior**: Offer bilingual support and ensure the patient understands the process regardless of their primary language.
- **Severity**: High

---

This bug report highlights critical issues in the performance of the "Pretty Good AI" agent. Prioritizing fixes in high and critical severity areas could significantly enhance the user experience for patients and improve the efficiency of the services provided.