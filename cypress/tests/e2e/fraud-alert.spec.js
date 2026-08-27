import userData from '../../fixtures/user-data.json'
import LoginPage from '../../pages/login.Page'
import Payment from '../../pages/payment.Page'

const loginPage = new LoginPage()
const payment = new Payment()

describe('Alerta de fraude na transação', () => {
    it('Deve completar a transação e exibir o alerta de fraude (cenário 1)', () => {
        loginPage.accessLoginPage()
        loginPage.loginWithUser(userData.userVeteran.username, userData.userVeteran.password)

        payment.paymentWithFraudAlert(5000, 'transferencia teste fraude', 'Herrerafurt')
        payment.checkPayment()

        cy.get('[data-test="alert-bar-warning"]', { timeout: 10000 })
            .should('be.visible')
            .and('contain', 'fraude')
    })

    it('Deve repetir o fluxo na mesma sessão e exibir o alerta novamente (cenário 2 — regressão do child preso em loading)', () => {
        loginPage.accessLoginPage()
        loginPage.loginWithUser(userData.userVeteran.username, userData.userVeteran.password)

        payment.paymentWithFraudAlert(5000, 'transferencia teste fraude 1', 'Herrerafurt')
        payment.checkPayment()
        cy.get('[data-test="alert-bar-warning"]', { timeout: 10000 })
            .should('be.visible')
            .and('contain', 'fraude')

        payment.paymentWithFraudAlert(7500, 'transferencia teste fraude 2', 'Herrerafurt', true)
        payment.checkPayment()
        cy.get('[data-test="alert-bar-warning"]', { timeout: 10000 })
            .should('be.visible')
            .and('contain', 'fraude')
    })
})