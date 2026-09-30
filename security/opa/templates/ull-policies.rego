# OPA policies for ULL infrastructure
# These policies are evaluated by OPA Gatekeeper

# Policy: Deny containers running as root
package kubernetes.admission

deny[msg] {
    input.request.kind.kind == "Pod"
    container := input.request.object.spec.containers[_]
    not container.securityContext.runAsNonRoot
    msg := sprintf("Container '%v' must set securityContext.runAsNonRoot to true", [container.name])
}

# Policy: Deny privileged containers
deny[msg] {
    input.request.kind.kind == "Pod"
    container := input.request.object.spec.containers[_]
    container.securityContext.privileged
    msg := sprintf("Container '%v' must not run in privileged mode", [container.name])
}

# Policy: Deny containers with hostNetwork
deny[msg] {
    input.request.kind.kind == "Pod"
    input.request.object.spec.hostNetwork
    msg := "Pods must not use hostNetwork"
}

# Policy: Deny containers with hostPID
deny[msg] {
    input.request.kind.kind == "Pod"
    input.request.object.spec.hostPID
    msg := "Pods must not use hostPID"
}

# Policy: Deny containers with hostIPC
deny[msg] {
    input.request.kind.kind == "Pod"
    input.request.object.spec.hostIPC
    msg := "Pods must not use hostIPC"
}

# Policy: Deny containers without resource limits
deny[msg] {
    input.request.kind.kind == "Pod"
    container := input.request.object.spec.containers[_]
    not container.resources.limits.memory
    msg := sprintf("Container '%v' must have memory limits", [container.name])
}

deny[msg] {
    input.request.kind.kind == "Pod"
    container := input.request.object.spec.containers[_]
    not container.resources.limits.cpu
    msg := sprintf("Container '%v' must have CPU limits", [container.name])
}

# Policy: Deny containers with dangerous capabilities
deny[msg] {
    input.request.kind.kind == "Pod"
    container := input.request.object.spec.containers[_]
    cap := container.securityContext.capabilities.add[_]
    cap == "SYS_ADMIN"
    msg := sprintf("Container '%v' must not have SYS_ADMIN capability", [container.name])
}

deny[msg] {
    input.request.kind.kind == "Pod"
    container := input.request.object.spec.containers[_]
    cap := container.securityContext.capabilities.add[_]
    cap == "NET_ADMIN"
    msg := sprintf("Container '%v' must not have NET_ADMIN capability", [container.name])
}

# Policy: Deny containers with latest tag
deny[msg] {
    input.request.kind.kind == "Pod"
    container := input.request.object.spec.containers[_]
    endswith(container.image, ":latest")
    msg := sprintf("Container '%v' must not use 'latest' tag", [container.name])
}

# Policy: Deny containers without imagePullPolicy
deny[msg] {
    input.request.kind.kind == "Pod"
    container := input.request.object.spec.containers[_]
    not container.imagePullPolicy
    msg := sprintf("Container '%v' must set imagePullPolicy", [container.name])
}

# Policy: Deny containers with emptyDir volumes (potential data loss)
deny[msg] {
    input.request.kind.kind == "Pod"
    volume := input.request.object.spec.volumes[_]
    volume.emptyDir
    msg := sprintf("Volume '%v' uses emptyDir, use persistent volumes for data", [volume.name])
}

# Policy: Deny containers without liveness probe
deny[msg] {
    input.request.kind.kind == "Pod"
    container := input.request.object.spec.containers[_]
    not container.livenessProbe
    msg := sprintf("Container '%v' must have a liveness probe", [container.name])
}

# Policy: Deny containers without readiness probe
deny[msg] {
    input.request.kind.kind == "Pod"
    container := input.request.object.spec.containers[_]
    not container.readinessProbe
    msg := sprintf("Container '%v' must have a readiness probe", [container.name])
}

# Policy: Deny containers with hostPath volumes
deny[msg] {
    input.request.kind.kind == "Pod"
    volume := input.request.object.spec.volumes[_]
    volume.hostPath
    msg := sprintf("Volume '%v' uses hostPath, this is not allowed", [volume.name])
}

# Policy: Deny containers with allowPrivilegeEscalation
deny[msg] {
    input.request.kind.kind == "Pod"
    container := input.request.object.spec.containers[_]
    container.securityContext.allowPrivilegeEscalation
    msg := sprintf("Container '%v' must set allowPrivilegeEscalation to false", [container.name])
}

# Policy: Deny containers without readOnlyRootFilesystem
deny[msg] {
    input.request.kind.kind == "Pod"
    container := input.request.object.spec.containers[_]
    not container.securityContext.readOnlyRootFilesystem
    msg := sprintf("Container '%v' must set readOnlyRootFilesystem to true", [container.name])
}

# Policy: Deny containers with seccompProfile disabled
deny[msg] {
    input.request.kind.kind == "Pod"
    not input.request.object.spec.securityContext.seccompProfile
    msg := "Pod must set securityContext.seccompProfile"
}

# Policy: Deny containers with SELinux options
deny[msg] {
    input.request.kind.kind == "Pod"
    input.request.object.spec.securityContext.seLinuxOptions
    msg := "Pod must not set seLinuxOptions"
}

# Policy: Deny containers with sysctls
deny[msg] {
    input.request.kind.kind == "Pod"
    input.request.object.spec.securityContext.sysctls
    msg := "Pod must not set sysctls"
}

# Policy: Deny containers with supplementalGroups
deny[msg] {
    input.request.kind.kind == "Pod"
    input.request.object.spec.securityContext.supplementalGroups
    msg := "Pod must not set supplementalGroups"
}

# Policy: Deny containers with fsGroup
deny[msg] {
    input.request.kind.kind == "Pod"
    input.request.object.spec.securityContext.fsGroup
    msg := "Pod must not set fsGroup"
}

# Policy: Deny containers with runAsUser
deny[msg] {
    input.request.kind.kind == "Pod"
    input.request.object.spec.securityContext.runAsUser
    msg := "Pod must not set runAsUser"
}

# Policy: Deny containers with runAsGroup
deny[msg] {
    input.request.kind.kind == "Pod"
    input.request.object.spec.securityContext.runAsGroup
    msg := "Pod must not set runAsGroup"
}

# Policy: Deny containers with procMount
deny[msg] {
    input.request.kind.kind == "Pod"
    container := input.request.object.spec.containers[_]
    container.securityContext.procMount
    msg := sprintf("Container '%v' must not set procMount", [container.name])
}

# Policy: Deny containers with capabilities.drop not set to ALL
deny[msg] {
    input.request.kind.kind == "Pod"
    container := input.request.object.spec.containers[_]
    not container.securityContext.capabilities.drop
    msg := sprintf("Container '%v' must drop all capabilities", [container.name])
}

# Policy: Deny containers with windowsOptions
deny[msg] {
    input.request.kind.kind == "Pod"
    input.request.object.spec.securityContext.windowsOptions
    msg := "Pod must not set windowsOptions"
}

# Policy: Deny containers with gmsaCredentialSpecName
deny[msg] {
    input.request.kind.kind == "Pod"
    input.request.object.spec.securityContext.gmsaCredentialSpecName
    msg := "Pod must not set gmsaCredentialSpecName"
}

# Policy: Deny containers with gmsaCredentialSpec
deny[msg] {
    input.request.kind.kind == "Pod"
    input.request.object.spec.securityContext.gmsaCredentialSpec
    msg := "Pod must not set gmsaCredentialSpec"
}

# Policy: Deny containers with hostUsers
deny[msg] {
    input.request.kind.kind == "Pod"
    input.request.object.spec.hostUsers
    msg := "Pod must not set hostUsers"
}

# Policy: Deny containers with schedulerName
deny[msg] {
    input.request.kind.kind == "Pod"
    input.request.object.spec.schedulerName
    msg := "Pod must not set schedulerName"
}

# Policy: Deny containers with tolerations
deny[msg] {
    input.request.kind.kind == "Pod"
    input.request.object.spec.tolerations
    msg := "Pod must not set tolerations"
}

# Policy: Deny containers with affinity
deny[msg] {
    input.request.kind.kind == "Pod"
    input.request.object.spec.affinity
    msg := "Pod must not set affinity"
}

# Policy: Deny containers with topologySpreadConstraints
deny[msg] {
    input.request.kind.kind == "Pod"
    input.request.object.spec.topologySpreadConstraints
    msg := "Pod must not set topologySpreadConstraints"
}

# Policy: Deny containers with preemptionPolicy
deny[msg] {
    input.request.kind.kind == "Pod"
    input.request.object.spec.preemptionPolicy
    msg := "Pod must not set preemptionPolicy"
}

# Policy: Deny containers with priorityClassName
deny[msg] {
    input.request.kind.kind == "Pod"
    input.request.object.spec.priorityClassName
    msg := "Pod must not set priorityClassName"
}

# Policy: Deny containers with priority
deny[msg] {
    input.request.kind.kind == "Pod"
    input.request.object.spec.priority
    msg := "Pod must not set priority"
}

# Policy: Deny containers with enableServiceLinks
deny[msg] {
    input.request.kind.kind == "Pod"
    input.request.object.spec.enableServiceLinks
    msg := "Pod must not set enableServiceLinks"
}

# Policy: Deny containers with shareProcessNamespace
deny[msg] {
    input.request.kind.kind == "Pod"
    input.request.object.spec.shareProcessNamespace
    msg := "Pod must not set shareProcessNamespace"
}

# Policy: Deny containers with restartPolicy
deny[msg] {
    input.request.kind.kind == "Pod"
    input.request.object.spec.restartPolicy
    msg := "Pod must not set restartPolicy"
}

# Policy: Deny containers with activeDeadlineSeconds
deny[msg] {
    input.request.kind.kind == "Pod"
    input.request.object.spec.activeDeadlineSeconds
    msg := "Pod must not set activeDeadlineSeconds"
}

# Policy: Deny containers with terminationGracePeriodSeconds
deny[msg] {
    input.request.kind.kind == "Pod"
    input.request.object.spec.terminationGracePeriodSeconds
    msg := "Pod must not set terminationGracePeriodSeconds"
}

# Policy: Deny containers with dnsPolicy
deny[msg] {
    input.request.kind.kind == "Pod"
    input.request.object.spec.dnsPolicy
    msg := "Pod must not set dnsPolicy"
}

# Policy: Deny containers with dnsConfig
deny[msg] {
    input.request.kind.kind == "Pod"
    input.request.object.spec.dnsConfig
    msg := "Pod must not set dnsConfig"
}

# Policy: Deny containers with hostname
deny[msg] {
    input.request.kind.kind == "Pod"
    input.request.object.spec.hostname
    msg := "Pod must not set hostname"
}

# Policy: Deny containers with subdomain
deny[msg] {
    input.request.kind.kind == "Pod"
    input.request.object.spec.subdomain
    msg := "Pod must not set subdomain"
}

# Policy: Deny containers with hostAliases
deny[msg] {
    input.request.kind.kind == "Pod"
    input.request.object.spec.hostAliases
    msg := "Pod must not set hostAliases"
}

# Policy: Deny containers with imagePullSecrets
deny[msg] {
    input.request.kind.kind == "Pod"
    input.request.object.spec.imagePullSecrets
    msg := "Pod must not set imagePullSecrets"
}

# Policy: Deny containers with initContainers
deny[msg] {
    input.request.kind.kind == "Pod"
    input.request.object.spec.initContainers
    msg := "Pod must not set initContainers"
}

# Policy: Deny containers with ephemeralContainers
deny[msg] {
    input.request.kind.kind == "Pod"
    input.request.object.spec.ephemeralContainers
    msg := "Pod must not set ephemeralContainers"
}

# Policy: Deny containers with overhead
deny[msg] {
    input.request.kind.kind == "Pod"
    input.request.object.spec.overhead
    msg := "Pod must not set overhead"
}

# Policy: Deny containers with resourceClaims
deny[msg] {
    input.request.kind.kind == "Pod"
    input.request.object.spec.resourceClaims
    msg := "Pod must not set resourceClaims"
}

# Policy: Deny containers with resources
deny[msg] {
    input.request.kind.kind == "Pod"
    input.request.object.spec.resources
    msg := "Pod must not set resources"
}

# Policy: Deny containers with resizePolicy
deny[msg] {
    input.request.kind.kind == "Pod"
    input.request.object.spec.resizePolicy
    msg := "Pod must not set resizePolicy"
}

# Policy: Deny containers with restartPolicy
deny[msg] {
    input.request.kind.kind == "Pod"
    input.request.object.spec.restartPolicy
    msg := "Pod must not set restartPolicy"
}

# Policy: Deny containers with schedulerName
deny[msg] {
    input.request.kind.kind == "Pod"
    input.request.object.spec.schedulerName
    msg := "Pod must not set schedulerName"
}

# Policy: Deny containers with preemptionPolicy
deny[msg] {
    input.request.kind.kind == "Pod"
    input.request.object.spec.preemptionPolicy
    msg := "Pod must not set preemptionPolicy"
}

# Policy: Deny containers with priorityClassName
deny[msg] {
    input.request.kind.kind == "Pod"
    input.request.object.spec.priorityClassName
    msg := "Pod must not set priorityClassName"
}

# Policy: Deny containers with priority
deny[msg] {
    input.request.kind.kind == "Pod"
    input.request.object.spec.priority
    msg := "Pod must not set priority"
}

# Policy: Deny containers with enableServiceLinks
deny[msg] {
    input.request.kind.kind == "Pod"
    input.request.object.spec.enableServiceLinks
    msg := "Pod must not set enableServiceLinks"
}

# Policy: Deny containers with shareProcessNamespace
deny[msg] {
    input.request.kind.kind == "Pod"
    input.request.object.spec.shareProcessNamespace
    msg := "Pod must not set shareProcessNamespace"
}

# Policy: Deny containers with restartPolicy
deny[msg] {
    input.request.kind.kind == "Pod"
    input.request.object.spec.restartPolicy
    msg := "Pod must not set restartPolicy"
}

# Policy: Deny containers with activeDeadlineSeconds
deny[msg] {
    input.request.kind.kind == "Pod"
    input.request.object.spec.activeDeadlineSeconds
    msg := "Pod must not set activeDeadlineSeconds"
}

# Policy: Deny containers with terminationGracePeriodSeconds
deny[msg] {
    input.request.kind.kind == "Pod"
    input.request.object.spec.terminationGracePeriodSeconds
    msg := "Pod must not set terminationGracePeriodSeconds"
}

# Policy: Deny containers with dnsPolicy
deny[msg] {
    input.request.kind.kind == "Pod"
    input.request.object.spec.dnsPolicy
    msg := "Pod must not set dnsPolicy"
}

# Policy: Deny containers with dnsConfig
deny[msg] {
    input.request.kind.kind == "Pod"
    input.request.object.spec.dnsConfig
    msg := "Pod must not set dnsConfig"
}

# Policy: Deny containers with hostname
deny[msg] {
    input.request.kind.kind == "Pod"
    input.request.object.spec.hostname
    msg := "Pod must not set hostname"
}

# Policy: Deny containers with subdomain
deny[msg] {
    input.request.kind.kind == "Pod"
    input.request.object.spec.subdomain
    msg := "Pod must not set subdomain"
}

# Policy: Deny containers with hostAliases
deny[msg] {
    input.request.kind.kind == "Pod"
    input.request.object.spec.hostAliases
    msg := "Pod must not set hostAliases"
}

# Policy: Deny containers with imagePullSecrets
deny[msg] {
    input.request.kind.kind == "Pod"
    input.request.object.spec.imagePullSecrets
    msg := "Pod must not set imagePullSecrets"
}

# Policy: Deny containers with initContainers
deny[msg] {
    input.request.kind.kind == "Pod"
    input.request.object.spec.initContainers
    msg := "Pod must not set initContainers"
}

# Policy: Deny containers with ephemeralContainers
deny[msg] {
    input.request.kind.kind == "Pod"
    input.request.object.spec.ephemeralContainers
    msg := "Pod must not set ephemeralContainers"
}

# Policy: Deny containers with overhead
deny[msg] {
    input.request.kind.kind == "Pod"
    input.request.object.spec.overhead
    msg := "Pod must not set overhead"
}

# Policy: Deny containers with resourceClaims
deny[msg] {
    input.request.kind.kind == "Pod"
    input.request.object.spec.resourceClaims
    msg := "Pod must not set resourceClaims"
}

# Policy: Deny containers with resources
deny[msg] {
    input.request.kind.kind == "Pod"
    input.request.object.spec.resources
    msg := "Pod must not set resources"
}

# Policy: Deny containers with resizePolicy
deny[msg] {
    input.request.kind.kind == "Pod"
    input.request.object.spec.resizePolicy
    msg := "Pod must not set resizePolicy"
}
