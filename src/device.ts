import { SendMessageCommand } from "@aws-sdk/client-sqs"

import { queueClient } from "./index"

const BEACHES_QUEUE = ["long_beach", "venice_beach", "santa_monica_beach", "manhattan_beach"]

const SQS_QUEUE_URL = process.env.ENDPOINT + "/000000000000/"

let result
//get timestamp
let new_Date = Date.now().toString()
let fullDate = new Date().toLocaleString()

//generates a random integer between two values, inclusive
const getValue = (min: number, max: number) => {
  min = Math.ceil(min)
  max = Math.floor(max)
  return Math.floor(Math.random() * (max - min + 1) + min)
}

const uploadToQueues = async (sqsQueueUrl = SQS_QUEUE_URL) => {
  for (let queue = 0; queue < BEACHES_QUEUE.length; queue++) {
    let randomDeviceIterations = getValue(2, 5)

    for (let count = 0; count < randomDeviceIterations; count++) {
      const command = new SendMessageCommand({
        QueueUrl: SQS_QUEUE_URL + BEACHES_QUEUE[queue],
        DelaySeconds: 1,
        MessageBody: `{ "beach":"${BEACHES_QUEUE[queue].toString()}","ph":"${getValue(
          0,
          14
        ).toString()}","hydrocarbons":"${getValue(0, 10).toString()} µg/L","eCholi":"${getValue(
          0,
          500
        ).toString()} UFC/100ml","bacterias":"${getValue(
          0,
          200
        ).toString()} bacterias/100ml","timeStamp":"${new_Date}","dayTime":"${fullDate}"}`,
      })
      const response = await queueClient.send(command)

      if (!response) {
        console.error("Error sending to queue", BEACHES_QUEUE[queue])
      }
      console.info("Message sent")
    }
  }
}
uploadToQueues()
