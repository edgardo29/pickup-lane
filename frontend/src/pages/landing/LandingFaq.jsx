import { Plus } from 'lucide-react'
import { faqs } from './landingData.js'

function LandingFaq() {
  return (
    <section className="landing-section landing-faq" aria-labelledby="landing-faq-title">
      <div className="landing-section__header">
        <p className="landing-section__eyebrow">Questions</p>
        <h2 id="landing-faq-title">What players usually ask first.</h2>
      </div>

      <div className="landing-faq__list">
        {faqs.map((faq) => (
          <details className="landing-faq__item" key={faq.question}>
            <summary>
              <span>{faq.question}</span>
              <Plus aria-hidden="true" />
            </summary>
            <p>{faq.answer}</p>
          </details>
        ))}
      </div>
    </section>
  )
}

export default LandingFaq
