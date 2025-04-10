# Creating an IAM User.

When interacting with AWS services, it is important to create an IAM user with the necessary permissions. This user will be used by the SRE agent to interact with AWS services.

There already exists an IAM user group called `sre-agent` that contains the necessary permissions for the SRE agent.

To create a new IAM user with the necessary permissions, follow these steps:

1. Visit the [IAM Users dashboard](https://us-east-1.console.aws.amazon.com/iam/home?region=eu-west-2#/users)

2. Click on the `Create user` button.

![iam-users-dashboard](imgs/iam/iam-users-dashboard.png)

3. Enter a user name for the new user.

![iam-user-details](imgs/iam/iam-user-details.png)

4. Add the user to the `sre-agent` group.

![iam-set-permissions](imgs/iam/iam-set-permissions.png)

5. Confirm the creation of the user.

![create-user](imgs/iam/create-user.png)

6. Create an access key for the new user.

![add-access-creds](imgs/iam/add-access-creds.png)

7. (Additional) Give the user access to the Kubernetes cluster.
  a. Under the cluster that you want to give access in the [EKS dashboard](https://eu-west-2.console.aws.amazon.com/eks/clusters?region=eu-west-2) select the Access tab.
  ![eks-access-tab](imgs/iam/eks-access-tab.png)
  b. Select `Create access entry`.
  c. Select the user you just created.
  ![give-user-access-to-eks](imgs/iam/give-user-access-to-eks.png)
  d. Select the policy you want to give the user access to, we only need `AmazonEKSViewPolicy` for our purposes.
  ![add-access-policy](imgs/iam/add-access-policy.png)
